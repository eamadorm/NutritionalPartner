import io
from datetime import datetime, timezone
from typing import Optional

from loguru import logger
from pypdf import PdfReader

from backend.smae_engine.source_code.bq_service.main import BqService
from backend.smae_engine.source_code.bq_service.schemas import LoadResponse
from backend.smae_engine.source_code.config import (
    BqSettings,
    GcsSettings,
    GeminiSettings,
)
from backend.smae_engine.source_code.gcs_service.main import GcsService
from backend.smae_engine.source_code.gemini_service.main import GeminiService
from backend.smae_engine.source_code.gemini_service.schemas import (
    ExtractResponse,
    TransformResponse,
    VerificationResponse,
)
from backend.smae_engine.source_code.schemas import (
    ExtractionMetadata,
    ExtractionRequest,
    ExtractionResponse,
)


class IngestionPipeline:
    """
    Thin orchestrator for the SMAE PDF extraction pipeline.
    Composes GcsService, GeminiService, and BqService into a single run() entry point.
    All infrastructure logic lives in the respective service modules.
    """

    def __init__(
        self,
        gcs_settings: Optional[GcsSettings] = None,
        gemini_settings: Optional[GeminiSettings] = None,
        bq_settings: Optional[BqSettings] = None,
    ) -> None:
        self._gcs = GcsService(gcs_settings or GcsSettings())
        self._gemini = GeminiService(gemini_settings or GeminiSettings())
        self._bq = BqService(bq_settings or BqSettings())

    def run(self, request: ExtractionRequest) -> ExtractionResponse:
        """
        Orchestrates the full extraction pipeline end-to-end.

        Args:
            request: ExtractionRequest -> Validated request with GCS URI and optional page params.

        Returns:
            ExtractionResponse -> Validated response containing items and metadata.
        """
        logger.info(f"Pipeline started for bucket: {request.gcs_uri.split('/')[2]}")
        self._gcs.validate_trusted_bucket(request.gcs_uri)
        extract_result = self.extract_parallel(request)
        transform_result = self.transform(extract_result)
        metadata = ExtractionMetadata(
            source_uri=request.gcs_uri,
            processed_at=datetime.now(timezone.utc),
        )
        response = ExtractionResponse(items=transform_result.items, metadata=metadata)
        self.verify(response)
        self.load(transform_result, source_uri=request.gcs_uri)
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
        mime_type = self._gcs.get_mime_type(request.gcs_uri)
        return self._gemini.extract(request.gcs_uri, mime_type)

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
        download = self._gcs.download_pdf(request.gcs_uri)
        pages = self._resolve_pages(request, download.pdf_bytes)
        return self._gemini.extract_parallel_paged(
            request.gcs_uri, download.pdf_bytes, pages
        )

    def transform(self, response: ExtractResponse) -> TransformResponse:
        """
        Builds validated FoodItem models from raw extracted data.

        Args:
            response: ExtractResponse -> Raw items and source URI from extract step.

        Returns:
            TransformResponse -> Validated and enriched FoodItem models.
        """
        return self._gemini.transform(response)

    def verify(self, response: ExtractionResponse) -> VerificationResponse:
        """
        Verifies structural integrity of the extraction response.

        Args:
            response: ExtractionResponse -> Final response with validated items.

        Returns:
            VerificationResponse -> Status and count of verified items.
        """
        return self._gemini.verify(response.items)

    def load(
        self, transform_result: TransformResponse, source_uri: str
    ) -> LoadResponse:
        """
        Persists validated FoodItems to BigQuery using SCD Type 2 strategy.

        Args:
            transform_result: TransformResponse -> Validated FoodItem models from transform step.
            source_uri: str -> GCS URI of the originating PDF document.

        Returns:
            LoadResponse -> Counts of inserted, failed, and dead-letter rows.
        """
        return self._bq.load(transform_result.items, source_uri)

    # --- Private helpers (orchestration-level only) ---

    def _resolve_pages(self, request: ExtractionRequest, pdf_bytes: bytes) -> list[int]:
        """Returns the ordered list of 1-indexed page numbers to process.

        Args:
            request: ExtractionRequest -> Request with optional page_range or pages.
            pdf_bytes: bytes -> Raw PDF bytes used to determine total page count.

        Returns:
            list[int] -> Ordered page numbers to process.
        """
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


if __name__ == "__main__":
    pipeline = IngestionPipeline()
    # Full document (single-pass):
    # request = ExtractionRequest(gcs_uri="gs://nutritional-data-sources/smae.pdf")
    # Parallel batch (pages 1-200, 5 pages per batch):
    # request = ExtractionRequest(gcs_uri="gs://nutritional-data-sources/smae.pdf", page_range=(1, 200))
    # response = pipeline.run(request)
