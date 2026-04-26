from typing import Annotated, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SmaeSettings(BaseSettings):
    """
    Configuration settings for the SMAE ingestion pipeline.
    Loads from environment variables prefixed with ``SMAE_``.
    """

    model_config = SettingsConfigDict(env_prefix="SMAE_")

    gemini_model: Annotated[
        str,
        Field(default="gemini-2.5-flash", description="Gemini model identifier"),
    ]
    gcp_location: Annotated[
        str,
        Field(default="us-central1", description="GCP region for Vertex AI"),
    ]
    trusted_bucket: Annotated[
        str,
        Field(
            default="nutritional-data-sources",
            description="Allowed GCS bucket name",
        ),
    ]
    max_file_size_mb: Annotated[
        int,
        Field(default=20, ge=1, description="Maximum allowed PDF size in MB"),
    ]
    batch_size: Annotated[
        int,
        Field(default=5, ge=1, description="Pages per parallel extraction batch"),
    ]
    max_parallel_workers: Annotated[
        int,
        Field(default=10, ge=1, description="Max concurrent Gemini batch calls"),
    ]
    max_source_pdf_size_mb: Annotated[
        int,
        Field(
            default=50, ge=1, description="Max source PDF size in MB before download"
        ),
    ]
    gemini_max_retries: Annotated[
        int,
        Field(default=3, ge=0, description="Max retries on Gemini ResourceExhausted"),
    ]
    gemini_retry_base_delay_s: Annotated[
        float,
        Field(default=5.0, ge=0.1, description="Base retry delay in seconds"),
    ]
    gemini_retry_max_delay_s: Annotated[
        float,
        Field(default=60.0, ge=1.0, description="Max retry delay cap in seconds"),
    ]

    # --- BigQuery ---
    bq_project: Annotated[
        Optional[str],
        Field(
            default=None,
            description="GCP project for BigQuery writes; resolved from ADC when unset",
        ),
    ]
    bq_dataset: Annotated[
        str,
        Field(
            default="nutrimental_information",
            description="BigQuery dataset containing the food equivalents table",
        ),
    ]
    bq_table: Annotated[
        str,
        Field(default="food_equivalents", description="BigQuery table for food items"),
    ]
    bq_dead_letter_table: Annotated[
        str,
        Field(
            default="food_equivalents_dead_letter",
            description="BigQuery dead-letter table for failed row inserts",
        ),
    ]
    bq_batch_size: Annotated[
        int,
        Field(
            default=500,
            ge=1,
            description="Max rows per load_table_from_json batch job",
        ),
    ]
