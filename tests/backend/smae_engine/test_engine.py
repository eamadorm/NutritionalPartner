import io
import json
from concurrent.futures import TimeoutError as FutureTimeoutError
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from pypdf import PdfReader, PdfWriter
from google.genai import errors as genai_errors

from backend.smae_engine.source_code.config import (
    BqSettings,
    GcsSettings,
    GeminiSettings,
)
from backend.smae_engine.source_code.schemas import (
    ExtractionMetadata,
    ExtractionRequest,
    ExtractionResponse,
    ExtractResponse,
    FoodItem,
    LoadResponse,
    TransformResponse,
    VerificationResponse,
)
from backend.smae_engine.source_code.pipeline import IngestionPipeline


def make_pdf(num_pages: int) -> bytes:
    """Creates a minimal in-memory PDF with blank pages for testing."""
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=100, height=100)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.fixture
def pipeline() -> IngestionPipeline:
    return IngestionPipeline()


@pytest.fixture
def sample_item() -> FoodItem:
    return FoodItem(
        food_uuid="test-uuid",
        food="Apple",
        energy_kcal=50,
        protein_g=0.3,
        ingested_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_response(sample_item: FoodItem) -> ExtractionResponse:
    metadata = ExtractionMetadata(
        source_uri="gs://test",
        processed_at=datetime.now(timezone.utc),
    )
    return ExtractionResponse(items=[sample_item], metadata=metadata)


# --- _generate_food_uuid ---


def test_generate_food_uuid_is_deterministic(pipeline: IngestionPipeline):
    uuid1 = pipeline._gemini._generate_food_uuid("gs://test.pdf", "Apple")
    uuid2 = pipeline._gemini._generate_food_uuid("gs://test.pdf", "Apple")
    assert uuid1 == uuid2


def test_generate_food_uuid_differs_by_food(pipeline: IngestionPipeline):
    uuid1 = pipeline._gemini._generate_food_uuid("gs://test.pdf", "Apple")
    uuid2 = pipeline._gemini._generate_food_uuid("gs://test.pdf", "Banana")
    assert uuid1 != uuid2


def test_generate_food_uuid_differs_by_uri(pipeline: IngestionPipeline):
    uuid1 = pipeline._gemini._generate_food_uuid("gs://bucket-a/file.pdf", "Apple")
    uuid2 = pipeline._gemini._generate_food_uuid("gs://bucket-b/file.pdf", "Apple")
    assert uuid1 != uuid2


# --- transform ---


def test_transform_assigns_uuid_and_timestamp(pipeline: IngestionPipeline):
    raw = [{"food": "Carrot", "energy_kcal": 41}]
    result = pipeline.transform(
        ExtractResponse(raw_items=raw, source_uri="gs://test.pdf")
    )
    assert isinstance(result, TransformResponse)
    assert len(result.items) == 1
    assert result.items[0].food == "Carrot"
    assert result.items[0].food_uuid != "temp"
    assert result.items[0].ingested_at is not None


def test_transform_unknown_food_name_fallback(pipeline: IngestionPipeline):
    raw = [{"food": None, "energy_kcal": 10}]
    result = pipeline.transform(
        ExtractResponse(raw_items=raw, source_uri="gs://test.pdf")
    )
    assert result.items[0].food_uuid == pipeline._gemini._generate_food_uuid(
        "gs://test.pdf", "unknown"
    )


def test_transform_empty_list_returns_empty(pipeline: IngestionPipeline):
    assert (
        pipeline.transform(
            ExtractResponse(raw_items=[], source_uri="gs://test.pdf")
        ).items
        == []
    )


# --- verify ---


def test_verify_happy_path(
    pipeline: IngestionPipeline, sample_response: ExtractionResponse
):
    result = pipeline.verify(sample_response)
    assert result.status == "valid"
    assert result.items_count == 1


def test_verify_empty_response_is_valid(pipeline: IngestionPipeline):
    metadata = ExtractionMetadata(
        source_uri="gs://test",
        processed_at=datetime.now(timezone.utc),
    )
    response = ExtractionResponse(items=[], metadata=metadata)
    result = pipeline.verify(response)
    assert result.status == "valid"
    assert result.items_count == 0


def test_verify_all_optional_fields_null_is_valid(pipeline: IngestionPipeline):
    metadata = ExtractionMetadata(
        source_uri="gs://test",
        processed_at=datetime.now(timezone.utc),
    )
    item = FoodItem(food_uuid="test-uuid", ingested_at=datetime.now(timezone.utc))
    response = ExtractionResponse(items=[item], metadata=metadata)
    assert pipeline.verify(response).status == "valid"


# --- Pydantic schema validation (failure modes) ---


def test_food_item_rejects_negative_energy():
    with pytest.raises(ValidationError) as exc_info:
        FoodItem(
            food_uuid="test-uuid",
            food="Apple",
            energy_kcal=-10,
            ingested_at=datetime.now(timezone.utc),
        )
    assert "greater than or equal to 0" in str(exc_info.value)


def test_food_item_rejects_negative_protein():
    with pytest.raises(ValidationError) as exc_info:
        FoodItem(
            food_uuid="test-uuid",
            food="Apple",
            protein_g=-1.5,
            ingested_at=datetime.now(timezone.utc),
        )
    assert "greater than or equal to 0" in str(exc_info.value)


def test_food_item_rejects_negative_lipids():
    with pytest.raises(ValidationError) as exc_info:
        FoodItem(
            food_uuid="test-uuid",
            lipids_g=-0.1,
            ingested_at=datetime.now(timezone.utc),
        )
    assert "greater than or equal to 0" in str(exc_info.value)


# --- ExtractionRequest.validate_gcs_uri ---


def test_extraction_request_accepts_valid_gcs_uri():
    request = ExtractionRequest(gcs_uri="gs://nutritional-data-sources/smae.pdf")
    assert request.gcs_uri == "gs://nutritional-data-sources/smae.pdf"


def test_extraction_request_accepts_nested_path_uri():
    uri = "gs://my-bucket/folder/subfolder/file.pdf"
    request = ExtractionRequest(gcs_uri=uri)
    assert request.gcs_uri == uri


def test_extraction_request_accepts_dots_and_underscores_in_bucket():
    uri = "gs://my.bucket_name/file.pdf"
    request = ExtractionRequest(gcs_uri=uri)
    assert request.gcs_uri == uri


@pytest.mark.parametrize(
    "invalid_uri",
    [
        "https://malicious.com/file.pdf",
        "gs://",
        "gs://bucket/file.txt",
        "gs://bucket/",
        "",
        "gs://UPPERCASE/file.pdf",
    ],
)
def test_extraction_request_rejects_invalid_gcs_uri(invalid_uri: str):
    with pytest.raises(ValidationError) as exc_info:
        ExtractionRequest(gcs_uri=invalid_uri)
    assert "gcs_uri must match" in str(exc_info.value)


# --- FoodItem max_length constraints ---


def test_food_item_rejects_food_exceeding_max_length():
    with pytest.raises(ValidationError) as exc_info:
        FoodItem(
            food_uuid="test-uuid",
            food="a" * 201,
            ingested_at=datetime.now(timezone.utc),
        )
    assert "at most 200 characters" in str(exc_info.value)


def test_food_item_rejects_unit_exceeding_max_length():
    with pytest.raises(ValidationError) as exc_info:
        FoodItem(
            food_uuid="test-uuid",
            unit="u" * 51,
            ingested_at=datetime.now(timezone.utc),
        )
    assert "at most 50 characters" in str(exc_info.value)


# --- VerificationResponse ---


def test_verification_response_happy_path():
    response = VerificationResponse(status="valid", items_count=5)
    assert response.status == "valid"
    assert response.items_count == 5


def test_verification_response_rejects_negative_items_count():
    with pytest.raises(ValidationError) as exc_info:
        VerificationResponse(status="valid", items_count=-1)
    assert "greater than or equal to 0" in str(exc_info.value)


# --- _validate_trusted_bucket ---


def test_validate_trusted_bucket_passes_when_bucket_matches():
    pipeline = IngestionPipeline(gcs_settings=GcsSettings(trusted_bucket="my-bucket"))
    # Should not raise
    pipeline._gcs.validate_trusted_bucket("gs://my-bucket/file.pdf")


def test_validate_trusted_bucket_raises_when_bucket_differs():
    pipeline = IngestionPipeline(gcs_settings=GcsSettings(trusted_bucket="my-bucket"))
    with pytest.raises(ValueError) as exc_info:
        pipeline._gcs.validate_trusted_bucket("gs://malicious-bucket/file.pdf")
    assert "Untrusted bucket: malicious-bucket" in str(exc_info.value)


# --- _get_mime_type ---


def test_get_mime_type_returns_blob_content_type_when_present(mocker):
    pipeline = IngestionPipeline(gcs_settings=GcsSettings(trusted_bucket="my-bucket"))
    mock_blob = mocker.Mock()
    mock_blob.content_type = "application/pdf"
    mock_blob.size = 1024
    mock_bucket = mocker.Mock()
    mock_bucket.get_blob.return_value = mock_blob
    mock_client = mocker.Mock()
    mock_client.bucket.return_value = mock_bucket
    pipeline._gcs._client = mock_client

    result = pipeline._gcs.get_mime_type("gs://my-bucket/file.pdf")

    assert result == "application/pdf"
    mock_client.bucket.assert_called_once_with("my-bucket")
    mock_bucket.get_blob.assert_called_once_with("file.pdf")


def test_get_mime_type_falls_back_to_default_when_blob_is_none(mocker):
    pipeline = IngestionPipeline(gcs_settings=GcsSettings(trusted_bucket="my-bucket"))
    mock_bucket = mocker.Mock()
    mock_bucket.get_blob.return_value = None
    mock_client = mocker.Mock()
    mock_client.bucket.return_value = mock_bucket
    pipeline._gcs._client = mock_client

    result = pipeline._gcs.get_mime_type("gs://my-bucket/file.pdf")

    assert result == "application/pdf"
    mock_bucket.get_blob.assert_called_once_with("file.pdf")


def test_get_mime_type_falls_back_to_default_when_content_type_is_none(mocker):
    pipeline = IngestionPipeline(gcs_settings=GcsSettings(trusted_bucket="my-bucket"))
    mock_blob = mocker.Mock()
    mock_blob.content_type = None
    mock_blob.size = 1024
    mock_bucket = mocker.Mock()
    mock_bucket.get_blob.return_value = mock_blob
    mock_client = mocker.Mock()
    mock_client.bucket.return_value = mock_bucket
    pipeline._gcs._client = mock_client

    result = pipeline._gcs.get_mime_type("gs://my-bucket/file.pdf")

    assert result == "application/pdf"


def test_get_mime_type_falls_back_to_default_when_content_type_is_empty(mocker):
    pipeline = IngestionPipeline(gcs_settings=GcsSettings(trusted_bucket="my-bucket"))
    mock_blob = mocker.Mock()
    mock_blob.content_type = ""
    mock_blob.size = 1024
    mock_bucket = mocker.Mock()
    mock_bucket.get_blob.return_value = mock_blob
    mock_client = mocker.Mock()
    mock_client.bucket.return_value = mock_bucket
    pipeline._gcs._client = mock_client

    result = pipeline._gcs.get_mime_type("gs://my-bucket/file.pdf")

    assert result == "application/pdf"


def test_get_mime_type_lazily_initializes_storage_client_when_missing(mocker):
    pipeline = IngestionPipeline(gcs_settings=GcsSettings(trusted_bucket="my-bucket"))
    mock_blob = mocker.Mock()
    mock_blob.content_type = "application/pdf"
    mock_blob.size = 1024
    mock_bucket = mocker.Mock()
    mock_bucket.get_blob.return_value = mock_blob
    mock_client_instance = mocker.Mock()
    mock_client_instance.bucket.return_value = mock_bucket
    mock_storage_client_cls = mocker.patch(
        "backend.smae_engine.source_code.gcs_service.main.storage.Client",
        return_value=mock_client_instance,
    )

    result = pipeline._gcs.get_mime_type("gs://my-bucket/file.pdf")

    assert result == "application/pdf"
    mock_storage_client_cls.assert_called_once_with()
    assert pipeline._gcs._client is mock_client_instance


def test_get_mime_type_raises_when_file_exceeds_max_size(mocker):
    pipeline = IngestionPipeline(
        gcs_settings=GcsSettings(trusted_bucket="my-bucket", max_file_size_mb=1)
    )
    mock_blob = mocker.Mock()
    mock_blob.content_type = "application/pdf"
    mock_blob.size = 2 * 1024 * 1024  # 2 MB > 1 MB limit
    mock_bucket = mocker.Mock()
    mock_bucket.get_blob.return_value = mock_blob
    mock_client = mocker.Mock()
    mock_client.bucket.return_value = mock_bucket
    pipeline._gcs._client = mock_client

    with pytest.raises(ValueError, match="exceeds maximum size"):
        pipeline._gcs.get_mime_type("gs://my-bucket/large.pdf")


# --- _call_gemini ---


def test_call_gemini_returns_parsed_json_on_happy_path(mocker):
    pipeline = IngestionPipeline(gcs_settings=GcsSettings(trusted_bucket="my-bucket"))
    mock_response = mocker.Mock()
    mock_response.text = '[{"food": "Apple"}]'
    mock_client = mocker.Mock()
    mock_client.models.generate_content.return_value = mock_response
    file_part = mocker.Mock()

    result = pipeline._gemini._call_gemini(mock_client, file_part)

    assert result == [{"food": "Apple"}]
    mock_client.models.generate_content.assert_called_once()
    call_kwargs = mock_client.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == pipeline._gemini._settings.model
    assert file_part in call_kwargs["contents"]


def test_call_gemini_raises_json_decode_error_when_response_not_json(mocker):
    pipeline = IngestionPipeline(gcs_settings=GcsSettings(trusted_bucket="my-bucket"))
    mock_response = mocker.Mock()
    mock_response.text = "not valid json"
    mock_client = mocker.Mock()
    mock_client.models.generate_content.return_value = mock_response
    file_part = mocker.Mock()

    with pytest.raises(json.JSONDecodeError):
        pipeline._gemini._call_gemini(mock_client, file_part)


def test_call_gemini_retries_on_api_error_429_then_succeeds(mocker):
    """Happy path retry: APIError(429) on first attempt, success on second."""
    pipeline = IngestionPipeline(
        gcs_settings=GcsSettings(trusted_bucket="my-bucket"),
        gemini_settings=GeminiSettings(max_retries=2),
    )
    mock_response = mocker.Mock()
    mock_response.text = '[{"food": "Rice"}]'
    mock_client = mocker.Mock()
    mock_client.models.generate_content.side_effect = [
        genai_errors.APIError(429, {}),
        mock_response,
    ]
    mocker.patch("backend.smae_engine.source_code.gemini_service.main.time.sleep")
    file_part = mocker.Mock()

    result = pipeline._gemini._call_gemini(mock_client, file_part)

    assert result == [{"food": "Rice"}]
    assert mock_client.models.generate_content.call_count == 2


def test_call_gemini_does_not_retry_on_non_retryable_status(mocker):
    """Failure mode: APIError with status 403 must be re-raised immediately."""
    pipeline = IngestionPipeline(
        gcs_settings=GcsSettings(trusted_bucket="my-bucket"),
        gemini_settings=GeminiSettings(max_retries=3),
    )
    mock_client = mocker.Mock()
    mock_client.models.generate_content.side_effect = genai_errors.APIError(403, {})
    file_part = mocker.Mock()

    with pytest.raises(genai_errors.APIError) as exc_info:
        pipeline._gemini._call_gemini(mock_client, file_part)

    assert exc_info.value.code == 403
    assert mock_client.models.generate_content.call_count == 1


def test_call_gemini_exhausts_retries_and_reraises(mocker):
    """Failure mode: APIError(429) persists through all attempts; final raise propagates."""
    pipeline = IngestionPipeline(
        gcs_settings=GcsSettings(trusted_bucket="my-bucket"),
        gemini_settings=GeminiSettings(max_retries=2),
    )
    mock_client = mocker.Mock()
    mock_client.models.generate_content.side_effect = genai_errors.APIError(429, {})
    mocker.patch("backend.smae_engine.source_code.gemini_service.main.time.sleep")
    file_part = mocker.Mock()

    with pytest.raises(genai_errors.APIError) as exc_info:
        pipeline._gemini._call_gemini(mock_client, file_part)

    assert exc_info.value.code == 429
    # max_retries=2 means 3 total attempts (attempts 0, 1, 2)
    assert mock_client.models.generate_content.call_count == 3


def test_process_batches_parallel_raises_when_future_times_out(mocker):
    """Failure mode: future.result() TimeoutError propagates out of _process_batches_parallel."""
    pipeline = IngestionPipeline(
        gcs_settings=GcsSettings(trusted_bucket="my-bucket"),
        gemini_settings=GeminiSettings(max_parallel_workers=2),
    )
    # Directly inject a FutureTimeoutError via the future mock so no real sleep is needed.
    mock_future = mocker.Mock()
    mock_future.result.side_effect = FutureTimeoutError()
    mock_executor = mocker.MagicMock()
    mock_executor.__enter__ = mocker.Mock(return_value=mock_executor)
    mock_executor.__exit__ = mocker.Mock(return_value=False)
    mock_executor.submit.return_value = mock_future
    mocker.patch(
        "backend.smae_engine.source_code.gemini_service.main.ThreadPoolExecutor",
        return_value=mock_executor,
    )
    mocker.patch(
        "backend.smae_engine.source_code.gemini_service.main.as_completed",
        return_value=[mock_future],
    )

    with pytest.raises(FutureTimeoutError):
        pipeline._gemini._process_batches_parallel(make_pdf(1), [[1]])


# --- _build_client ---


def test_build_client_initializes_genai_client_with_correct_args(mocker):
    pipeline = IngestionPipeline(
        gcs_settings=GcsSettings(trusted_bucket="my-bucket"),
        gemini_settings=GeminiSettings(gcp_location="us-east1"),
    )
    mocker.patch(
        "backend.smae_engine.source_code.gemini_service.main.google.auth.default",
        return_value=(None, "test-project"),
    )
    mock_genai_client_cls = mocker.patch(
        "backend.smae_engine.source_code.gemini_service.main.genai.Client"
    )

    pipeline._gemini._build_client()

    call_kwargs = mock_genai_client_cls.call_args.kwargs
    assert call_kwargs["vertexai"] is True
    assert call_kwargs["project"] == "test-project"
    assert call_kwargs["location"] == "us-east1"
    assert call_kwargs["http_options"].timeout == int(3500.0 * 1000)


def test_build_client_caches_client_across_calls(mocker):
    pipeline = IngestionPipeline(gcs_settings=GcsSettings(trusted_bucket="my-bucket"))
    mocker.patch(
        "backend.smae_engine.source_code.gemini_service.main.google.auth.default",
        return_value=(None, "test-project"),
    )
    mock_genai_client_cls = mocker.patch(
        "backend.smae_engine.source_code.gemini_service.main.genai.Client"
    )

    first = pipeline._gemini._build_client()
    second = pipeline._gemini._build_client()

    assert mock_genai_client_cls.call_count == 1
    assert first is second


# --- run() integration ---


def test_run_orchestrates_extract_transform_verify_in_order(mocker, sample_item):
    pipeline = IngestionPipeline(
        gcs_settings=GcsSettings(trusted_bucket="nutritional-data-sources")
    )
    request = ExtractionRequest(gcs_uri="gs://nutritional-data-sources/sample.pdf")
    extract_response = ExtractResponse(
        raw_items=[{"food": "Apple"}],
        source_uri=request.gcs_uri,
    )
    transform_response = TransformResponse(items=[sample_item])
    verification_response = VerificationResponse(status="valid", items_count=1)

    mock_extract_parallel = mocker.patch.object(
        pipeline, "extract_parallel", return_value=extract_response
    )
    mock_transform = mocker.patch.object(
        pipeline, "transform", return_value=transform_response
    )
    mock_verify = mocker.patch.object(
        pipeline, "verify", return_value=verification_response
    )

    mock_load = mocker.patch.object(
        pipeline,
        "load",
        return_value=LoadResponse(rows_inserted=1, rows_failed=0, dead_letter_rows=0),
    )

    response = pipeline.run(request)

    assert isinstance(response, ExtractionResponse)
    assert response.items == [sample_item]
    assert response.metadata.source_uri == request.gcs_uri

    mock_extract_parallel.assert_called_once_with(request)
    mock_transform.assert_called_once_with(extract_response)
    mock_verify.assert_called_once()
    verify_arg = mock_verify.call_args.args[0]
    assert isinstance(verify_arg, ExtractionResponse)
    assert verify_arg.items == [sample_item]
    mock_load.assert_called_once_with(transform_response, source_uri=request.gcs_uri)


def test_run_propagates_validation_error_without_calling_extract(mocker):
    pipeline = IngestionPipeline(gcs_settings=GcsSettings(trusted_bucket="my-bucket"))
    request = ExtractionRequest(gcs_uri="gs://other-bucket/file.pdf")
    mock_extract_parallel = mocker.patch.object(pipeline, "extract_parallel")
    mock_transform = mocker.patch.object(pipeline, "transform")
    mock_verify = mocker.patch.object(pipeline, "verify")

    with pytest.raises(ValueError) as exc_info:
        pipeline.run(request)

    assert "Untrusted bucket: other-bucket" in str(exc_info.value)
    mock_extract_parallel.assert_not_called()
    mock_transform.assert_not_called()
    mock_verify.assert_not_called()


# --- run() routing ---


def test_extraction_request_accepts_valid_page_range():
    req = ExtractionRequest(
        gcs_uri="gs://nutritional-data-sources/smae.pdf", page_range=(1, 10)
    )
    assert req.page_range == (1, 10)


def test_extraction_request_rejects_page_range_start_less_than_one():
    with pytest.raises(ValidationError, match="page_range start must be >= 1"):
        ExtractionRequest(
            gcs_uri="gs://nutritional-data-sources/smae.pdf", page_range=(0, 5)
        )


def test_extraction_request_rejects_page_range_end_before_start():
    with pytest.raises(ValidationError, match="page_range end must be >= start"):
        ExtractionRequest(
            gcs_uri="gs://nutritional-data-sources/smae.pdf", page_range=(5, 3)
        )


# --- ExtractionRequest.pages validator ---


def test_extraction_request_accepts_valid_pages_and_sorts_them():
    req = ExtractionRequest(
        gcs_uri="gs://nutritional-data-sources/smae.pdf", pages=[3, 1, 2]
    )
    assert req.pages == [1, 2, 3]


def test_extraction_request_rejects_empty_pages_list():
    with pytest.raises(ValidationError, match="pages list cannot be empty"):
        ExtractionRequest(gcs_uri="gs://nutritional-data-sources/smae.pdf", pages=[])


def test_extraction_request_rejects_pages_less_than_one():
    with pytest.raises(ValidationError, match="all page numbers must be >= 1"):
        ExtractionRequest(
            gcs_uri="gs://nutritional-data-sources/smae.pdf", pages=[0, 1, 2]
        )


def test_extraction_request_deduplicates_pages():
    req = ExtractionRequest(
        gcs_uri="gs://nutritional-data-sources/smae.pdf", pages=[2, 2, 1]
    )
    assert req.pages == [1, 2]


# --- ExtractionRequest page selection exclusivity ---


def test_extraction_request_rejects_both_page_range_and_pages():
    with pytest.raises(
        ValidationError, match="Cannot specify both page_range and pages"
    ):
        ExtractionRequest(
            gcs_uri="gs://nutritional-data-sources/smae.pdf",
            page_range=(1, 5),
            pages=[1, 2],
        )


# --- GCS URI security: trailing newline bypass ---


def test_extraction_request_rejects_gcs_uri_with_trailing_newline():
    with pytest.raises(ValidationError):
        ExtractionRequest(gcs_uri="gs://nutritional-data-sources/smae.pdf\n")


# --- _download_pdf ---


def test_download_pdf_returns_bytes_from_gcs(mocker):
    pipeline = IngestionPipeline(gcs_settings=GcsSettings(trusted_bucket="my-bucket"))
    mock_blob = mocker.Mock()
    mock_blob.size = 1024
    mock_blob.download_as_bytes.return_value = b"pdf content"
    mock_bucket = mocker.Mock()
    mock_bucket.blob.return_value = mock_blob
    mock_client = mocker.Mock()
    mock_client.bucket.return_value = mock_bucket
    pipeline._gcs._client = mock_client

    result = pipeline._gcs.download_pdf("gs://my-bucket/file.pdf")

    assert result.pdf_bytes == b"pdf content"
    mock_blob.reload.assert_called_once()
    mock_blob.download_as_bytes.assert_called_once()


def test_download_pdf_raises_when_file_exceeds_max_source_size(mocker):
    pipeline = IngestionPipeline(
        gcs_settings=GcsSettings(trusted_bucket="my-bucket", max_source_pdf_size_mb=1)
    )
    mock_blob = mocker.Mock()
    mock_blob.size = 2 * 1024 * 1024
    mock_bucket = mocker.Mock()
    mock_bucket.blob.return_value = mock_blob
    mock_client = mocker.Mock()
    mock_client.bucket.return_value = mock_bucket
    pipeline._gcs._client = mock_client

    with pytest.raises(ValueError, match="Source PDF exceeds"):
        pipeline._gcs.download_pdf("gs://my-bucket/large.pdf")


# --- _resolve_pages ---


def test_resolve_pages_returns_all_pages_when_no_params(pipeline):
    request = ExtractionRequest(gcs_uri="gs://nutritional-data-sources/smae.pdf")
    pages = pipeline._resolve_pages(request, make_pdf(5))
    assert pages == [1, 2, 3, 4, 5]


def test_resolve_pages_returns_specific_pages_when_pages_specified(pipeline):
    request = ExtractionRequest(
        gcs_uri="gs://nutritional-data-sources/smae.pdf", pages=[2, 4]
    )
    pages = pipeline._resolve_pages(request, make_pdf(5))
    assert pages == [2, 4]


def test_resolve_pages_returns_range_when_page_range_specified(pipeline):
    request = ExtractionRequest(
        gcs_uri="gs://nutritional-data-sources/smae.pdf", page_range=(2, 4)
    )
    pages = pipeline._resolve_pages(request, make_pdf(5))
    assert pages == [2, 3, 4]


def test_resolve_pages_clamps_page_range_end_to_document_length(pipeline):
    request = ExtractionRequest(
        gcs_uri="gs://nutritional-data-sources/smae.pdf", page_range=(3, 100)
    )
    pages = pipeline._resolve_pages(request, make_pdf(5))
    assert pages == [3, 4, 5]


def test_resolve_pages_raises_when_specific_pages_exceed_document_length(pipeline):
    request = ExtractionRequest(
        gcs_uri="gs://nutritional-data-sources/smae.pdf", pages=[2, 10]
    )
    with pytest.raises(ValueError, match="Pages out of range"):
        pipeline._resolve_pages(request, make_pdf(5))


# --- _build_batches ---


def test_build_batches_splits_pages_into_groups(pipeline):
    assert pipeline._gemini._build_batches([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_build_batches_single_batch_when_pages_fit(pipeline):
    assert pipeline._gemini._build_batches([1, 2, 3], 5) == [[1, 2, 3]]


def test_build_batches_one_page_per_batch_when_batch_size_is_one(pipeline):
    assert pipeline._gemini._build_batches([1, 2, 3], 1) == [[1], [2], [3]]


# --- _split_pdf_pages ---


def test_split_pdf_pages_produces_pdf_with_correct_page_count(pipeline):
    result = pipeline._gemini._split_pdf_pages(make_pdf(5), [1, 3, 5])
    reader = PdfReader(io.BytesIO(result))
    assert len(reader.pages) == 3


# --- _extract_single_batch ---


def test_extract_single_batch_calls_gemini_with_pdf_bytes(mocker, pipeline):
    mocker.patch.object(pipeline._gemini, "_build_client", return_value=mocker.Mock())
    mock_part_cls = mocker.patch(
        "backend.smae_engine.source_code.gemini_service.main.types.Part.from_bytes",
        return_value=mocker.Mock(),
    )
    mocker.patch.object(
        pipeline._gemini, "_call_gemini", return_value=[{"food": "Apple"}]
    )

    result = pipeline._gemini._extract_single_batch(make_pdf(2), [1, 2])

    assert result == [{"food": "Apple"}]
    mock_part_cls.assert_called_once()
    assert mock_part_cls.call_args.kwargs["mime_type"] == "application/pdf"


# --- _process_batches_parallel ---


def test_process_batches_parallel_merges_results_in_page_order(mocker):
    pipeline = IngestionPipeline(
        gcs_settings=GcsSettings(trusted_bucket="my-bucket"),
        gemini_settings=GeminiSettings(max_parallel_workers=2),
    )

    def fake_extract(pdf_bytes, pages):
        return [{"food": f"page-{p}"} for p in pages]

    mocker.patch.object(
        pipeline._gemini, "_extract_single_batch", side_effect=fake_extract
    )

    result = pipeline._gemini._process_batches_parallel(make_pdf(4), [[1, 2], [3, 4]])

    assert result == [
        {"food": "page-1"},
        {"food": "page-2"},
        {"food": "page-3"},
        {"food": "page-4"},
    ]


# --- run() routing ---


def test_run_routes_to_extract_parallel_when_page_range_given(mocker, sample_item):
    pipeline = IngestionPipeline(
        gcs_settings=GcsSettings(trusted_bucket="nutritional-data-sources")
    )
    request = ExtractionRequest(
        gcs_uri="gs://nutritional-data-sources/smae.pdf",
        page_range=(1, 10),
    )
    mock_parallel = mocker.patch.object(
        pipeline,
        "extract_parallel",
        return_value=ExtractResponse(raw_items=[], source_uri=request.gcs_uri),
    )
    mock_extract = mocker.patch.object(pipeline, "extract")
    mocker.patch.object(
        pipeline, "transform", return_value=TransformResponse(items=[sample_item])
    )
    mocker.patch.object(
        pipeline,
        "verify",
        return_value=VerificationResponse(status="valid", items_count=1),
    )
    mocker.patch.object(
        pipeline,
        "load",
        return_value=LoadResponse(rows_inserted=1, rows_failed=0, dead_letter_rows=0),
    )

    pipeline.run(request)

    mock_parallel.assert_called_once_with(request)
    mock_extract.assert_not_called()


def test_run_routes_to_extract_parallel_when_pages_list_given(mocker, sample_item):
    pipeline = IngestionPipeline(
        gcs_settings=GcsSettings(trusted_bucket="nutritional-data-sources")
    )
    request = ExtractionRequest(
        gcs_uri="gs://nutritional-data-sources/smae.pdf",
        pages=[1, 2, 3],
    )
    mock_parallel = mocker.patch.object(
        pipeline,
        "extract_parallel",
        return_value=ExtractResponse(raw_items=[], source_uri=request.gcs_uri),
    )
    mock_extract = mocker.patch.object(pipeline, "extract")
    mocker.patch.object(
        pipeline, "transform", return_value=TransformResponse(items=[sample_item])
    )
    mocker.patch.object(
        pipeline,
        "verify",
        return_value=VerificationResponse(status="valid", items_count=1),
    )
    mocker.patch.object(
        pipeline,
        "load",
        return_value=LoadResponse(rows_inserted=1, rows_failed=0, dead_letter_rows=0),
    )

    pipeline.run(request)

    mock_parallel.assert_called_once_with(request)
    mock_extract.assert_not_called()


# --- Security: _download_pdf post-download length check (F-01) ---


def test_download_pdf_raises_when_downloaded_bytes_exceed_limit(mocker):
    pipeline = IngestionPipeline(
        gcs_settings=GcsSettings(trusted_bucket="my-bucket", max_source_pdf_size_mb=1)
    )
    mock_blob = mocker.Mock()
    mock_blob.size = 512 * 1024  # 0.5 MB — passes pre-check
    oversized_bytes = b"x" * (2 * 1024 * 1024)  # 2 MB actual payload
    mock_pinned_blob = mocker.Mock()
    mock_pinned_blob.download_as_bytes.return_value = oversized_bytes
    mock_bucket = mocker.Mock()
    mock_bucket.blob.side_effect = [mock_blob, mock_pinned_blob]
    mock_client = mocker.Mock()
    mock_client.bucket.return_value = mock_bucket
    pipeline._gcs._client = mock_client

    with pytest.raises(ValueError, match="Source PDF exceeds"):
        pipeline._gcs.download_pdf("gs://my-bucket/file.pdf")


# --- Security: page_range 2000-page span cap (F-04) ---


def test_extraction_request_rejects_page_range_spanning_more_than_2000_pages():
    with pytest.raises(
        ValidationError, match="page_range cannot span more than 2000 pages"
    ):
        ExtractionRequest(
            gcs_uri="gs://nutritional-data-sources/smae.pdf",
            page_range=(1, 2001),
        )


def test_extraction_request_accepts_page_range_at_boundary():
    req = ExtractionRequest(
        gcs_uri="gs://nutritional-data-sources/smae.pdf",
        page_range=(1, 2000),
    )
    assert req.page_range == (1, 2000)


# --- Security: pages list max_length cap (F-04) ---


def test_extraction_request_rejects_pages_list_exceeding_2000_items():
    with pytest.raises(ValidationError):
        ExtractionRequest(
            gcs_uri="gs://nutritional-data-sources/smae.pdf",
            pages=list(range(1, 2002)),
        )


# --- Security: _resolve_pages raises on malformed PDF (F-02) ---


def test_resolve_pages_raises_on_malformed_pdf(pipeline):
    request = ExtractionRequest(gcs_uri="gs://nutritional-data-sources/smae.pdf")
    with pytest.raises(ValueError, match="Unable to parse source PDF"):
        pipeline._resolve_pages(request, b"this is not a pdf")


# --- TestLoad ---


class TestLoad:
    """Unit tests for IngestionPipeline.load() — BQ persistence with SCD Type 2."""

    @pytest.fixture
    def pipeline_with_settings(self) -> IngestionPipeline:
        return IngestionPipeline(
            gcs_settings=GcsSettings(trusted_bucket="nutritional-data-sources"),
            bq_settings=BqSettings(
                project="test-project",
                dataset="nutrimental_information",
                table="food_equivalents",
                dead_letter_table="food_equivalents_dead_letter",
                batch_size=500,
            ),
        )

    @pytest.fixture
    def sample_transform_response(self) -> TransformResponse:
        item = FoodItem(
            food_uuid="uuid-apple",
            food="Apple",
            energy_kcal=52,
            ingested_at=datetime.now(timezone.utc),
        )
        return TransformResponse(items=[item])

    def test_Load_ShouldInsertAllRows_WhenBQSucceeds(
        self, mocker, pipeline_with_settings, sample_transform_response
    ):
        """Happy path: load_table_from_json job completes without errors."""
        mock_job = mocker.Mock()
        mock_job.result.return_value = None

        mock_bq = mocker.Mock()
        mock_bq.query.return_value = mocker.Mock(**{"result.return_value": None})
        mock_bq.load_table_from_json.return_value = mock_job

        pipeline_with_settings._bq._client = mock_bq
        pipeline_with_settings._bq._settings = (
            pipeline_with_settings._bq._settings.model_copy(
                update={"project": "test-project"}
            )
        )

        result = pipeline_with_settings.load(
            sample_transform_response,
            source_uri="gs://nutritional-data-sources/smae.pdf",
        )

        assert isinstance(result, LoadResponse)
        assert result.rows_inserted == 1
        assert result.rows_failed == 0
        assert result.dead_letter_rows == 0
        mock_bq.load_table_from_json.assert_called_once()
        mock_bq.query.assert_called_once()

    def test_Load_ShouldWriteToDLT_WhenJobFails(
        self, mocker, pipeline_with_settings, sample_transform_response
    ):
        """Edge case: load job raises GoogleAPIError; rows must be routed to DLT."""
        from google.api_core.exceptions import GoogleAPIError

        mock_dlt_job = mocker.Mock()
        mock_dlt_job.result.return_value = None

        mock_bq = mocker.Mock()
        mock_bq.query.return_value = mocker.Mock(**{"result.return_value": None})
        mock_bq.load_table_from_json.side_effect = [
            GoogleAPIError("BQ job failed"),  # main table fails
            mock_dlt_job,  # DLT write succeeds
        ]

        pipeline_with_settings._bq._client = mock_bq
        pipeline_with_settings._bq._settings = (
            pipeline_with_settings._bq._settings.model_copy(
                update={"project": "test-project"}
            )
        )

        result = pipeline_with_settings.load(
            sample_transform_response,
            source_uri="gs://nutritional-data-sources/smae.pdf",
        )

        assert result.rows_inserted == 0
        assert result.rows_failed == 1
        assert result.dead_letter_rows == 1
        assert mock_bq.load_table_from_json.call_count == 2

    def test_Load_ShouldReturnZeroDeadLetterRows_WhenDLTWriteAlsoFails(
        self, mocker, pipeline_with_settings, sample_transform_response
    ):
        """Failure mode: both main load and DLT write fail; dead_letter_rows must be 0."""
        from google.api_core.exceptions import GoogleAPIError

        mock_bq = mocker.Mock()
        mock_bq.query.return_value = mocker.Mock(**{"result.return_value": None})
        mock_bq.load_table_from_json.side_effect = [
            GoogleAPIError("main table failure"),
            GoogleAPIError("DLT write failure"),
        ]

        pipeline_with_settings._bq._client = mock_bq
        pipeline_with_settings._bq._settings = (
            pipeline_with_settings._bq._settings.model_copy(
                update={"project": "test-project"}
            )
        )

        result = pipeline_with_settings.load(
            sample_transform_response,
            source_uri="gs://nutritional-data-sources/smae.pdf",
        )

        assert result.rows_inserted == 0
        assert result.rows_failed == 1
        assert result.dead_letter_rows == 0

    def test_Load_ShouldSkipDeactivationQuery_WhenItemsListIsEmpty(
        self, mocker, pipeline_with_settings
    ):
        """Edge case: empty items list must not trigger SCD deactivation query."""
        mock_bq = mocker.Mock()
        pipeline_with_settings._bq._client = mock_bq
        pipeline_with_settings._bq._settings = (
            pipeline_with_settings._bq._settings.model_copy(
                update={"project": "test-project"}
            )
        )

        result = pipeline_with_settings.load(
            TransformResponse(items=[]),
            source_uri="gs://nutritional-data-sources/smae.pdf",
        )

        assert result.rows_inserted == 0
        assert result.rows_failed == 0
        assert result.dead_letter_rows == 0
        mock_bq.query.assert_not_called()
        mock_bq.load_table_from_json.assert_not_called()

    def test_Load_ShouldRaiseRuntimeError_WhenBQClientFails(
        self, mocker, pipeline_with_settings, sample_transform_response
    ):
        """Failure mode: bigquery.Client() raises TransportError on construction."""
        from google.auth.exceptions import TransportError

        mocker.patch(
            "backend.smae_engine.source_code.bq_service.main.google.auth.default",
            side_effect=TransportError("Cannot reach metadata server"),
        )

        with pytest.raises(TransportError, match="Cannot reach metadata server"):
            pipeline_with_settings.load(
                sample_transform_response,
                source_uri="gs://nutritional-data-sources/smae.pdf",
            )
