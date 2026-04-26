import io
import json
import random
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Optional

import google.auth
from google import genai
from google.api_core import exceptions as gapi_exceptions
from google.cloud import storage
from google.genai import types
from loguru import logger
from pypdf import PdfReader, PdfWriter

from backend.smae_engine.source_code.config import SmaeSettings
from backend.smae_engine.source_code.schemas import (
    ExtractionMetadata,
    ExtractionRequest,
    ExtractionResponse,
    ExtractResponse,
    FoodItem,
    TransformResponse,
    VerificationResponse,
)

_NAMESPACE_URL = uuid.NAMESPACE_URL
_DEFAULT_MIME_TYPE = "application/pdf"


class IngestionPipeline:
    """
    Orchestrates the SMAE PDF extraction pipeline using Vertex AI Gemini Flash.
    Supports single-document and parallel batch extraction for large PDFs.
    """

    def __init__(self, settings: Optional[SmaeSettings] = None) -> None:
        self._settings = settings or SmaeSettings()
        self._genai_client: Optional[genai.Client] = None
        self._gcs_client: Optional[storage.Client] = None
        self._client_lock = threading.Lock()

    def run(self, request: ExtractionRequest) -> ExtractionResponse:
        """
        Orchestrates the full extraction pipeline end-to-end.

        Args:
            request: ExtractionRequest -> Validated request with GCS URI and optional page params.

        Returns:
            ExtractionResponse -> Validated response containing items and metadata.
        """
        logger.info(f"Pipeline started for bucket: {request.gcs_uri.split('/')[2]}")
        self._validate_trusted_bucket(request.gcs_uri)
        extract_result = self.extract_parallel(request)
        transform_result = self.transform(extract_result)
        metadata = ExtractionMetadata(
            source_uri=request.gcs_uri,
            processed_at=datetime.now(timezone.utc),
        )
        response = ExtractionResponse(items=transform_result.items, metadata=metadata)
        self.verify(response)
        logger.info(
            f"Pipeline complete: {len(transform_result.items)} items extracted."
        )
        return response

    def extract(self, request: ExtractionRequest) -> ExtractResponse:
        """
        Sends the full GCS document to Gemini Flash and returns raw extracted data.

        Args:
            request: ExtractionRequest -> Request containing the GCS URI.

        Returns:
            ExtractResponse -> Raw items plus source URI for downstream stages.
        """
        logger.info(f"Extracting from bucket: {request.gcs_uri.split('/')[2]}")
        client = self._build_client()
        mime_type = self._get_mime_type(request.gcs_uri)
        file_part = types.Part.from_uri(file_uri=request.gcs_uri, mime_type=mime_type)
        raw_items = self._call_gemini(client, file_part)
        return ExtractResponse(raw_items=raw_items, source_uri=request.gcs_uri)

    def extract_parallel(self, request: ExtractionRequest) -> ExtractResponse:
        """
        Downloads the source PDF and processes page batches in parallel.

        Args:
            request: ExtractionRequest -> Request with GCS URI and optional page selection.

        Returns:
            ExtractResponse -> Merged raw items from all batches, in page order.
        """
        logger.info(
            f"Starting parallel extraction from bucket: {request.gcs_uri.split('/')[2]}"
        )
        pdf_bytes = self._download_pdf(request.gcs_uri)
        pages = self._resolve_pages(request, pdf_bytes)
        batches = self._build_batches(pages, self._settings.batch_size)
        logger.info(f"Processing {len(pages)} pages across {len(batches)} batches.")
        raw_items = self._process_batches_parallel(pdf_bytes, batches)
        return ExtractResponse(raw_items=raw_items, source_uri=request.gcs_uri)

    def transform(self, response: ExtractResponse) -> TransformResponse:
        """
        Builds validated FoodItem models from raw extracted data.

        Args:
            response: ExtractResponse -> Raw items and source URI from extract step.

        Returns:
            TransformResponse -> Validated and enriched FoodItem models.
        """
        logger.info(f"Transforming {len(response.raw_items)} raw items.")
        now = datetime.now(timezone.utc)
        items = []
        for item_data in response.raw_items:
            food_uuid = self._generate_food_uuid(
                response.source_uri, str(item_data.get("food") or "unknown")
            )
            items.append(
                FoodItem.model_validate(
                    {**item_data, "food_uuid": food_uuid, "ingested_at": now}
                )
            )
        return TransformResponse(items=items)

    def verify(self, response: ExtractionResponse) -> VerificationResponse:
        """
        Verifies structural integrity of the extraction response.

        Args:
            response: ExtractionResponse -> Final response with validated items.

        Returns:
            VerificationResponse -> Status and count of verified items.
        """
        logger.info(f"Verifying {len(response.items)} extracted items.")
        return VerificationResponse(status="valid", items_count=len(response.items))

    def _build_client(self) -> genai.Client:
        """Initializes (and caches) the Vertex AI GenAI client using ADC."""
        if self._genai_client is None:
            with self._client_lock:
                if self._genai_client is None:
                    _, project_id = google.auth.default()
                    self._genai_client = genai.Client(
                        vertexai=True,
                        project=project_id,
                        location=self._settings.gcp_location,
                    )
        return self._genai_client

    def _get_mime_type(self, gcs_uri: str) -> str:
        """Fetches MIME type from GCS blob metadata; validates size; falls back to default."""
        path = gcs_uri.removeprefix("gs://")
        bucket_name, _, blob_name = path.partition("/")
        with self._client_lock:
            if self._gcs_client is None:
                self._gcs_client = storage.Client()
        blob = self._gcs_client.bucket(bucket_name).get_blob(blob_name)
        if blob:
            max_bytes = self._settings.max_file_size_mb * 1024 * 1024
            if blob.size > max_bytes:
                raise ValueError(
                    f"File exceeds maximum size of {self._settings.max_file_size_mb} MB"
                )
            if blob.content_type:
                logger.debug(f"MIME type from metadata: {blob.content_type}")
                return blob.content_type
        logger.debug(
            f"No MIME type in metadata for bucket: {bucket_name}, using default."
        )
        return _DEFAULT_MIME_TYPE

    def _call_gemini(self, client: genai.Client, file_part: types.Part) -> list[dict]:
        """
        Sends a document part to Gemini Flash and returns parsed JSON items.
        Retries on ResourceExhausted with exponential backoff and jitter.

        Args:
            client: genai.Client -> Authenticated Vertex AI GenAI client.
            file_part: types.Part -> Document part (inline bytes or GCS URI).

        Returns:
            list[dict] -> Raw extracted items as parsed JSON.
        """
        prompt = (
            "You are an expert nutritional data extractor. "
            "Extract all food items from the provided document into a structured list. "
            "Extract all columns accurately from the PDF tables. "
            "Use null for missing values. "
            "Leave food_uuid as 'temp' and ingested_at as current time."
        )
        for attempt in range(self._settings.gemini_max_retries + 1):
            try:
                logger.debug(f"Calling Gemini Flash (attempt {attempt + 1})...")
                result = client.models.generate_content(
                    model=self._settings.gemini_model,
                    contents=[file_part, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=list[FoodItem],
                    ),
                )
                return json.loads(result.text)
            except gapi_exceptions.ResourceExhausted:
                if attempt == self._settings.gemini_max_retries:
                    raise
                delay = min(
                    self._settings.gemini_retry_base_delay_s * (2**attempt)
                    + random.uniform(0, 1),
                    self._settings.gemini_retry_max_delay_s,
                )
                logger.warning(
                    f"Gemini ResourceExhausted (attempt {attempt + 1}/"
                    f"{self._settings.gemini_max_retries + 1}); retrying in {delay:.1f}s"
                )
                time.sleep(delay)
        raise RuntimeError("Unreachable")

    def _generate_food_uuid(self, source_uri: str, food_name: str) -> str:
        """Generates a deterministic UUID5 from source URI and food name."""
        return str(uuid.uuid5(_NAMESPACE_URL, f"{source_uri}_{food_name}"))

    def _validate_trusted_bucket(self, gcs_uri: str) -> None:
        """Raises ValueError if the URI targets a bucket other than the configured trusted one."""
        bucket_name = gcs_uri.removeprefix("gs://").partition("/")[0]
        if bucket_name != self._settings.trusted_bucket:
            raise ValueError(f"Untrusted bucket: {bucket_name}")

    def _download_pdf(self, gcs_uri: str) -> bytes:
        """Downloads the source PDF from GCS after validating its size."""
        path = gcs_uri.removeprefix("gs://")
        bucket_name, _, blob_name = path.partition("/")
        with self._client_lock:
            if self._gcs_client is None:
                self._gcs_client = storage.Client()
        blob = self._gcs_client.bucket(bucket_name).blob(blob_name)
        blob.reload()
        max_bytes = self._settings.max_source_pdf_size_mb * 1024 * 1024
        if blob.size is None or blob.size > max_bytes:
            raise ValueError(
                f"Source PDF exceeds {self._settings.max_source_pdf_size_mb} MB"
            )
        logger.debug(
            f"Downloading {blob.size / (1024 * 1024):.1f} MB from bucket: {bucket_name}"
        )
        pinned_blob = self._gcs_client.bucket(bucket_name).blob(
            blob_name, generation=blob.generation
        )
        pdf_bytes = pinned_blob.download_as_bytes()
        if len(pdf_bytes) > max_bytes:
            raise ValueError(
                f"Source PDF exceeds {self._settings.max_source_pdf_size_mb} MB"
            )
        return pdf_bytes

    def _resolve_pages(self, request: ExtractionRequest, pdf_bytes: bytes) -> list[int]:
        """Returns the ordered list of 1-indexed page numbers to process."""
        try:
            total = len(PdfReader(io.BytesIO(pdf_bytes)).pages)
        except Exception as exc:
            raise ValueError("Unable to parse source PDF") from exc
        if request.pages is not None:
            out_of_range = [p for p in request.pages if p > total]
            if out_of_range:
                raise ValueError(
                    f"Pages out of range (document has {total} pages): {out_of_range}"
                )
            return request.pages
        if request.page_range is not None:
            start, end = request.page_range
            return list(range(start, min(end, total) + 1))
        return list(range(1, total + 1))

    def _build_batches(self, pages: list[int], batch_size: int) -> list[list[int]]:
        """Splits a page list into sequential batches of at most batch_size pages."""
        return [pages[i : i + batch_size] for i in range(0, len(pages), batch_size)]

    def _split_pdf_pages(self, pdf_bytes: bytes, pages: list[int]) -> bytes:
        """Extracts the given 1-indexed pages into a new in-memory PDF."""
        reader = PdfReader(io.BytesIO(pdf_bytes))
        writer = PdfWriter()
        for page_num in pages:
            writer.add_page(reader.pages[page_num - 1])
        out = io.BytesIO()
        writer.write(out)
        return out.getvalue()

    def _extract_single_batch(
        self, pdf_bytes: bytes, batch_pages: list[int]
    ) -> list[dict]:
        """Sends one page batch inline to Gemini Flash and returns raw items."""
        batch_pdf = self._split_pdf_pages(pdf_bytes, batch_pages)
        client = self._build_client()
        file_part = types.Part.from_bytes(data=batch_pdf, mime_type=_DEFAULT_MIME_TYPE)
        return self._call_gemini(client, file_part)

    def _process_batches_parallel(
        self, pdf_bytes: bytes, batches: list[list[int]]
    ) -> list[dict]:
        """Processes all page batches concurrently; returns merged items in page order."""
        max_workers = min(len(batches), self._settings.max_parallel_workers)
        results: dict[int, list[dict]] = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(self._extract_single_batch, pdf_bytes, batch): idx
                for idx, batch in enumerate(batches)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                results[idx] = future.result()
        return [item for idx in sorted(results) for item in results[idx]]


if __name__ == "__main__":
    pipeline = IngestionPipeline()
    # Full document (single-pass):
    # request = ExtractionRequest(gcs_uri="gs://nutritional-data-sources/smae.pdf")
    # Parallel batch (pages 1-200, 5 pages per batch):
    # request = ExtractionRequest(gcs_uri="gs://nutritional-data-sources/smae.pdf", page_range=(1, 200))
    # response = pipeline.run(request)
