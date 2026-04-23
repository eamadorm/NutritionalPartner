import re
import uuid
import time
import json
import tempfile
from datetime import datetime, timezone
from typing import Optional
from loguru import logger

import vertexai
from vertexai.generative_models import GenerativeModel, Part
from google.cloud import storage, bigquery
from pypdf import PdfReader, PdfWriter

from .schemas import (
    ExtractionRequest,
    FoodItem,
    DeadLetterRecord,
    ExtractionMetadata,
    ExtractionResponse,
)
from .config import SMAEConfig


class SMAEEngine:
    """
    SMAE Engine for resilient nutritional data extraction using Gemini 2.5 Flash.
    """

    def __init__(self, config: Optional[SMAEConfig] = None) -> None:
        """
        Initializes the engine with configuration and GCP clients.

        Args:
            config: Optional[SMAEConfig] -> Configuration object
        """
        self.config = config or SMAEConfig()

        vertexai.init(project=self.config.PROJECT_ID, location=self.config.LOCATION)

        self.model = GenerativeModel(self.config.MODEL_NAME)
        self.storage_client = storage.Client(project=self.config.PROJECT_ID)
        self.bq_client = bigquery.Client(project=self.config.PROJECT_ID)

        self.main_table = f"{self.config.PROJECT_ID}.{self.config.DATASET_ID}.{self.config.TABLE_FOOD}"
        self.dlq_table = (
            f"{self.config.PROJECT_ID}.{self.config.DATASET_ID}.{self.config.TABLE_DLQ}"
        )

    def run(self, request: ExtractionRequest) -> ExtractionResponse:
        """
        Public entry point. Pydantic handles validation of 'request'.

        Args:
            request: ExtractionRequest -> Validated input parameters
        """
        start_time = time.time()
        logger.info(f"Starting pipeline for: {request.gcs_uri}")

        # Public method trust: request is already validated by Pydantic
        total_pages = self._get_page_count(request.gcs_uri)
        pages_to_process = self._determine_pages(request, total_pages)

        results: list[FoodItem] = []
        dead_letters: list[DeadLetterRecord] = []

        # Extract bucket name from validated URI
        temp_bucket = request.gcs_uri.split("/")[2]

        for page_idx in pages_to_process:
            page_num = page_idx + 1
            try:
                page_uri = self._extract_page_to_gcs(
                    request.gcs_uri, page_idx, temp_bucket
                )
                page_items = self._process_page(page_uri, page_num, request.gcs_uri)
                results.extend(page_items)

                self._cleanup_temp_blob(page_uri, temp_bucket)

            except Exception as e:
                logger.error(f"Page {page_num} failure: {str(e)}")
                dead_letters.append(
                    DeadLetterRecord(
                        source_uri=request.gcs_uri,
                        page_number=page_num,
                        error_message=str(e),
                        processed_at=datetime.now(timezone.utc),
                    )
                )

        if results:
            self._insert_to_bq(results, self.main_table)
        if dead_letters:
            self._insert_to_bq(dead_letters, self.dlq_table)

        metadata = ExtractionMetadata(
            total_items=len(results),
            processing_time_seconds=time.time() - start_time,
            source_blob=request.gcs_uri,
        )

        return ExtractionResponse(
            items=results, dead_letter_items=dead_letters, metadata=metadata
        )

    def _determine_pages(
        self, request: ExtractionRequest, total_pages: int
    ) -> list[int]:
        """Private method: assumes request is valid."""
        if request.specific_pages:
            return [p - 1 for p in request.specific_pages if 1 <= p <= total_pages]
        if request.page_range:
            start, end = request.page_range
            return list(range(max(0, start - 1), min(total_pages, end)))
        return list(range(total_pages))

    def _get_page_count(self, gcs_uri: str) -> int:
        """Private method: assumes gcs_uri is valid."""
        bucket_name = gcs_uri.split("/")[2]
        blob_path = "/".join(gcs_uri.split("/")[3:])

        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)

        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            blob.download_to_filename(tmp.name)
            reader = PdfReader(tmp.name)
            return len(reader.pages)

    def _extract_page_to_gcs(
        self, source_uri: str, page_num: int, target_bucket: str
    ) -> str:
        """Private method: assumes inputs are valid."""
        bucket_name = source_uri.split("/")[2]
        blob_path = "/".join(source_uri.split("/")[3:])
        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)

        with (
            tempfile.NamedTemporaryFile(suffix=".pdf") as tmp_in,
            tempfile.NamedTemporaryFile(suffix=".pdf") as tmp_out,
        ):
            blob.download_to_filename(tmp_in.name)
            reader = PdfReader(tmp_in.name)
            writer = PdfWriter()
            writer.add_page(reader.pages[page_num])

            with open(tmp_out.name, "wb") as f:
                writer.write(f)

            target_path = f"tmp_processing/{uuid.uuid4()}_page_{page_num}.pdf"
            target_blob = self.storage_client.bucket(target_bucket).blob(target_path)
            target_blob.upload_from_filename(tmp_out.name)

            return f"gs://{target_bucket}/{target_path}"

    def _process_page(
        self, page_uri: str, page_number: int, source_uri: str
    ) -> list[FoodItem]:
        """Private method: assumes inputs are valid."""
        prompt = """
        Analyze this SMAE table page.
        Return a JSON list of objects.
        Mandatory Keys: family_group, food, suggested_quantity, unit, gross_weight_grams, net_weight_grams, energy_kcal, protein_grams, lipids_grams, carbohidrates_grams, fiber_grams.
        If NO table is found, return an empty list [].
        """

        for attempt in range(3):
            try:
                doc = Part.from_uri(uri=page_uri, mime_type="application/pdf")
                response = self.model.generate_content([doc, prompt])

                # Cleanup markdown and parse
                clean_text = re.sub(r"```json\n?|\n?```", "", response.text).strip()
                raw_items = json.loads(clean_text)

                processed_at = datetime.now(timezone.utc)
                items = []
                for raw in raw_items:
                    # Pydantic handles item-level validation here
                    item = FoodItem(
                        **raw, processed_at=processed_at, page_number=page_number
                    )
                    item.generate_uuid(source_uri)
                    items.append(item)

                return items
            except Exception as e:
                if attempt == 2:
                    raise e
        return []

    def _cleanup_temp_blob(self, page_uri: str, bucket_name: str) -> None:
        """Private method."""
        blob_path = page_uri.replace(f"gs://{bucket_name}/", "")
        self.storage_client.bucket(bucket_name).blob(blob_path).delete()

    def _insert_to_bq(self, items: list, table_id: str) -> None:
        """Private method: items are already validated Pydantic objects."""
        ingestion_at = datetime.now(timezone.utc).isoformat()
        rows = []

        for item in items:
            row = item.dict()
            row["ingestion_at"] = ingestion_at
            # Serialization fix
            for k, v in row.items():
                if isinstance(v, datetime):
                    row[k] = v.isoformat()
            rows.append(row)

        errors = self.bq_client.insert_rows_json(table_id, rows)
        if errors:
            logger.error(f"BQ Insertion Errors in {table_id}: {errors}")
