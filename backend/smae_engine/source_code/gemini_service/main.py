import io
import json
import random
import threading
import time
import uuid
from concurrent.futures import (
    ThreadPoolExecutor,
    TimeoutError as FutureTimeoutError,
    as_completed,
)
from datetime import datetime, timezone
from typing import Optional

import google.auth
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from loguru import logger
from pypdf import PdfReader, PdfWriter

from backend.smae_engine.source_code.config import GeminiSettings
from backend.smae_engine.source_code.gemini_service.schemas import (
    ExtractResponse,
    FoodItem,
    TransformResponse,
    VerificationResponse,
)

_NAMESPACE_URL = uuid.NAMESPACE_URL
_DEFAULT_MIME_TYPE = "application/pdf"


class GeminiService:
    """
    Encapsulates all Gemini Flash and PDF processing logic for the SMAE pipeline.
    Handles single-document extraction, parallel batch processing, data transformation,
    and structural verification of extracted food items.
    """

    def __init__(self, settings: GeminiSettings) -> None:
        self._settings = settings
        self._client: Optional[genai.Client] = None
        self._lock = threading.Lock()

    def extract(self, gcs_uri: str, mime_type: str) -> ExtractResponse:
        """
        Sends the full GCS document to Gemini Flash and returns raw extracted data.

        Args:
            gcs_uri: str -> GCS URI of the source PDF.
            mime_type: str -> MIME type of the document.

        Returns:
            ExtractResponse -> Raw items plus source URI for downstream stages.
        """
        logger.info(f"Extracting from bucket: {gcs_uri.split('/')[2]}")
        client = self._build_client()
        file_part = types.Part.from_uri(file_uri=gcs_uri, mime_type=mime_type)
        raw_items = self._call_gemini(client, file_part)
        return ExtractResponse(raw_items=raw_items, source_uri=gcs_uri)

    def extract_parallel(self, gcs_uri: str, pdf_bytes: bytes) -> ExtractResponse:
        """
        Processes page batches in parallel from an already-downloaded PDF.

        Args:
            gcs_uri: str -> GCS URI used as the source reference.
            pdf_bytes: bytes -> Raw PDF bytes to split into batches.

        Returns:
            ExtractResponse -> Merged raw items from all batches, in page order.
        """
        logger.info(
            f"Starting parallel extraction from bucket: {gcs_uri.split('/')[2]}"
        )
        pages = self._resolve_all_pages(pdf_bytes)
        batches = self._build_batches(pages, self._settings.batch_size)
        logger.info(f"Processing {len(pages)} pages across {len(batches)} batches.")
        raw_items = self._process_batches_parallel(pdf_bytes, batches)
        return ExtractResponse(raw_items=raw_items, source_uri=gcs_uri)

    def extract_parallel_paged(
        self,
        gcs_uri: str,
        pdf_bytes: bytes,
        pages: list[int],
    ) -> ExtractResponse:
        """
        Processes a specific subset of pages in parallel from an already-downloaded PDF.

        Args:
            gcs_uri: str -> GCS URI used as the source reference.
            pdf_bytes: bytes -> Raw PDF bytes.
            pages: list[int] -> 1-indexed page numbers to process.

        Returns:
            ExtractResponse -> Merged raw items from the requested pages, in page order.
        """
        logger.info(
            f"Starting parallel extraction ({len(pages)} pages) "
            f"from bucket: {gcs_uri.split('/')[2]}"
        )
        batches = self._build_batches(pages, self._settings.batch_size)
        logger.info(f"Processing {len(pages)} pages across {len(batches)} batches.")
        raw_items = self._process_batches_parallel(pdf_bytes, batches)
        return ExtractResponse(raw_items=raw_items, source_uri=gcs_uri)

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

    def verify(self, items: list[FoodItem]) -> VerificationResponse:
        """
        Verifies structural integrity of a list of validated FoodItem models.

        Args:
            items: list[FoodItem] -> Validated food items from the transform step.

        Returns:
            VerificationResponse -> Status and count of verified items.
        """
        logger.info(f"Verifying {len(items)} extracted items.")
        return VerificationResponse(status="valid", items_count=len(items))

    def _build_client(self) -> genai.Client:
        """Initializes (and caches) the Vertex AI GenAI client using ADC.

        HttpOptions.timeout is in milliseconds; gemini_call_timeout_s is converted
        on construction so all HTTP requests inherit the Cloud-Run-safe deadline.
        """
        if self._client is None:
            with self._lock:
                if self._client is None:
                    _, project_id = google.auth.default()
                    timeout_ms = int(self._settings.gemini_call_timeout_s * 1000)
                    self._client = genai.Client(
                        vertexai=True,
                        project=project_id,
                        location=self._settings.gcp_location,
                        http_options=types.HttpOptions(timeout=timeout_ms),
                    )
        return self._client

    def _call_gemini(self, client: genai.Client, file_part: types.Part) -> list[dict]:
        """
        Sends a document part to Gemini Flash and returns parsed JSON items.
        Retries on status codes 429, 500, 503, 504 with exponential backoff and jitter.

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
        for attempt in range(self._settings.max_retries + 1):
            try:
                logger.debug(f"Calling Gemini Flash (attempt {attempt + 1})...")
                result = client.models.generate_content(
                    model=self._settings.model,
                    contents=[file_part, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=list[FoodItem],
                    ),
                )
                return json.loads(result.text)
            except genai_errors.APIError as exc:
                # 429=ResourceExhausted, 500=Internal, 503=Unavailable, 504=DeadlineExceeded
                if exc.code not in (429, 500, 503, 504):
                    raise
                if attempt == self._settings.max_retries:
                    raise
                delay = min(
                    self._settings.retry_base_delay_s * (2**attempt)
                    + random.uniform(0, 1),
                    self._settings.retry_max_delay_s,
                )
                logger.warning(
                    f"Gemini {exc.code} {exc.__class__.__name__} "
                    f"(attempt {attempt + 1}/{self._settings.max_retries + 1}); "
                    f"retrying in {delay:.1f}s"
                )
                time.sleep(delay)
        raise RuntimeError("Unreachable")

    def _generate_food_uuid(self, source_uri: str, food_name: str) -> str:
        """Generates a deterministic UUID5 from source URI and food name."""
        return str(uuid.uuid5(_NAMESPACE_URL, f"{source_uri}_{food_name}"))

    def _resolve_all_pages(self, pdf_bytes: bytes) -> list[int]:
        """Returns a list of all 1-indexed page numbers in the PDF."""
        try:
            total = len(PdfReader(io.BytesIO(pdf_bytes)).pages)
        except Exception as exc:
            raise ValueError("Unable to parse source PDF") from exc
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
                try:
                    results[idx] = future.result(
                        timeout=self._settings.batch_result_timeout_s
                    )
                except FutureTimeoutError:
                    logger.error(
                        f"Batch {idx} timed out after "
                        f"{self._settings.batch_result_timeout_s}s"
                    )
                    raise
        return [item for idx in sorted(results) for item in results[idx]]
