import json
import threading
from datetime import datetime, timezone
from typing import Optional

import google.auth
from google.cloud import bigquery
from loguru import logger

from backend.smae_engine.source_code.bq_service.schemas import (
    FoodEquivalentRow,
    LoadResponse,
)
from backend.smae_engine.source_code.config import BqSettings
from backend.smae_engine.source_code.gemini_service.schemas import FoodItem


class BqService:
    """
    Encapsulates all BigQuery interactions for the SMAE pipeline.
    Implements SCD Type 2 versioning via food_uuid, batch load jobs,
    and dead-letter routing for failed inserts.
    """

    def __init__(self, settings: BqSettings) -> None:
        self._settings = settings
        self._client: Optional[bigquery.Client] = None
        self._lock = threading.Lock()

    def load(self, items: list[FoodItem], source_uri: str) -> LoadResponse:
        """
        Persists validated FoodItems to BigQuery using SCD Type 2 strategy.
        Deactivates previous rows matching food_uuid before inserting new ones.
        Failed rows are routed to the dead-letter table.

        Args:
            items: list[FoodItem] -> Validated food items from the transform step.
            source_uri: str -> GCS URI of the originating PDF document.

        Returns:
            LoadResponse -> Counts of inserted, failed, and dead-letter rows.
        """
        logger.info(f"Loading {len(items)} rows to BigQuery.")
        bq = self._build_client()
        project = self._settings.project
        dataset = self._settings.dataset
        table_id = f"{project}.{dataset}.{self._settings.table}"
        dlt_id = f"{project}.{dataset}.{self._settings.dead_letter_table}"

        rows = self._build_rows(items, source_uri)
        self._deactivate_previous_rows(bq, table_id, rows)

        load_result = self._execute_load_job(bq, table_id, rows)
        dead_letter_count = self._route_to_dead_letter(
            bq, dlt_id, load_result["failed"], source_uri
        )

        logger.info(
            f"BQ load complete: {load_result['inserted']} inserted, "
            f"{len(load_result['failed'])} failed, {dead_letter_count} dead-lettered."
        )
        return LoadResponse(
            rows_inserted=load_result["inserted"],
            rows_failed=len(load_result["failed"]),
            dead_letter_rows=dead_letter_count,
        )

    def _build_client(self) -> bigquery.Client:
        """Initializes (and caches) the BigQuery client using ADC. No JSON key files."""
        if self._client is None:
            with self._lock:
                if self._client is None:
                    _, project_id = google.auth.default()
                    resolved_project = self._settings.project or project_id
                    self._settings = self._settings.model_copy(
                        update={"project": resolved_project}
                    )
                    self._client = bigquery.Client(project=resolved_project)
        return self._client

    def _build_rows(self, items: list[FoodItem], source_uri: str) -> list[dict]:
        """Converts FoodItem list to serialised BQ row dicts with source_uri and active=True.

        Args:
            items: list[FoodItem] -> Validated food items from the transform step.
            source_uri: str -> GCS URI of the originating PDF.

        Returns:
            list[dict] -> Serialised rows ready for load_table_from_json.
        """
        rows = []
        for item in items:
            row = FoodEquivalentRow(
                **item.model_dump(), source_uri=source_uri, active=True
            )
            rows.append(row.model_dump(mode="json"))
        return rows

    def _deactivate_previous_rows(
        self, bq: bigquery.Client, table_id: str, rows: list[dict]
    ) -> None:
        """Runs a parameterized DML UPDATE to mark existing rows inactive for the given food_uuids.

        Args:
            bq: bigquery.Client -> Authenticated BigQuery client.
            table_id: str -> Fully-qualified table id (project.dataset.table).
            rows: list[dict] -> New rows; food_uuid values used for the WHERE clause.
        """
        if not rows:
            return
        uuids = list({r["food_uuid"] for r in rows})
        # Build individual UNNEST-friendly param per UUID to stay safe with parameterization.
        # BQ does not support array parameters in IN clauses directly; use a subquery approach.
        placeholders = ", ".join(f"@uuid_{i}" for i in range(len(uuids)))
        query = (
            f"UPDATE `{table_id}` "
            f"SET active = FALSE "
            f"WHERE food_uuid IN ({placeholders}) AND active = TRUE"
        )
        query_params = [
            bigquery.ScalarQueryParameter(f"uuid_{i}", "STRING", uid)
            for i, uid in enumerate(uuids)
        ]
        job_config = bigquery.QueryJobConfig(query_parameters=query_params)
        logger.debug(f"SCD Type 2: deactivating {len(uuids)} previous rows.")
        bq.query(query, job_config=job_config).result()

    def _execute_load_job(
        self, bq: bigquery.Client, table_id: str, rows: list[dict]
    ) -> dict:
        """Writes rows to BQ using load_table_from_json and returns a result dict.

        Args:
            bq: bigquery.Client -> Authenticated BigQuery client.
            table_id: str -> Fully-qualified target table id.
            rows: list[dict] -> Serialised row dicts to write.

        Returns:
            dict -> {"inserted": int, "failed": list[dict]} counts.
        """
        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        )
        failed: list[dict] = []
        inserted = 0
        for start in range(0, len(rows), self._settings.batch_size):
            batch = rows[start : start + self._settings.batch_size]
            try:
                job = bq.load_table_from_json(batch, table_id, job_config=job_config)
                job.result()
                inserted += len(batch)
                logger.debug(f"BQ batch [{start}:{start + len(batch)}] loaded OK.")
            except Exception as exc:
                logger.warning(f"BQ batch [{start}:{start + len(batch)}] failed: {exc}")
                failed.extend(batch)
        return {"inserted": inserted, "failed": failed}

    def _route_to_dead_letter(
        self,
        bq: bigquery.Client,
        dlt_id: str,
        failed_rows: list[dict],
        source_uri: str,
    ) -> int:
        """Writes failed rows to the dead-letter table and returns the count written.

        Args:
            bq: bigquery.Client -> Authenticated BigQuery client.
            dlt_id: str -> Fully-qualified dead-letter table id.
            failed_rows: list[dict] -> Rows that failed to load to the main table.
            source_uri: str -> GCS URI for traceability in the DLT record.

        Returns:
            int -> Number of rows successfully routed to the dead-letter table.
        """
        if not failed_rows:
            return 0
        now_iso = datetime.now(timezone.utc).isoformat()
        dlt_rows = [
            {
                "source_uri": source_uri,
                "food_uuid": r.get("food_uuid"),
                "raw_row": json.dumps(r),
                "error_message": "load_table_from_json batch failure",
                "failed_at": now_iso,
            }
            for r in failed_rows
        ]
        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        )
        try:
            job = bq.load_table_from_json(dlt_rows, dlt_id, job_config=job_config)
            job.result()
            logger.warning(f"Dead-lettered {len(dlt_rows)} rows to {dlt_id}.")
            return len(dlt_rows)
        except Exception as exc:
            logger.error(f"Failed to write to dead-letter table: {exc}")
            return 0
