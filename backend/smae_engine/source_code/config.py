from typing import Annotated, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GcsSettings(BaseSettings):
    """
    Configuration settings for the GCS service.
    Loads from environment variables prefixed with ``SMAE_GCS_``.
    """

    model_config = SettingsConfigDict(env_prefix="SMAE_GCS_")

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
    max_source_pdf_size_mb: Annotated[
        int,
        Field(
            default=50, ge=1, description="Max source PDF size in MB before download"
        ),
    ]


class GeminiSettings(BaseSettings):
    """
    Configuration settings for the Gemini service.
    Loads from environment variables prefixed with ``SMAE_GEMINI_``.
    """

    model_config = SettingsConfigDict(env_prefix="SMAE_GEMINI_")

    model: Annotated[
        str,
        Field(default="gemini-2.5-flash", description="Gemini model identifier"),
    ]
    gcp_location: Annotated[
        str,
        Field(default="us-central1", description="GCP region for Vertex AI"),
    ]
    batch_size: Annotated[
        int,
        Field(default=5, ge=1, description="Pages per parallel extraction batch"),
    ]
    max_parallel_workers: Annotated[
        int,
        Field(default=10, ge=1, description="Max concurrent Gemini batch calls"),
    ]
    max_retries: Annotated[
        int,
        Field(
            default=3,
            ge=0,
            description=(
                "Max retries on retryable Gemini errors "
                "(ResourceExhausted, DeadlineExceeded, InternalServerError, ServiceUnavailable)"
            ),
        ),
    ]
    retry_base_delay_s: Annotated[
        float,
        Field(default=5.0, ge=0.1, description="Base retry delay in seconds"),
    ]
    retry_max_delay_s: Annotated[
        float,
        Field(default=60.0, ge=1.0, description="Max retry delay cap in seconds"),
    ]
    gemini_call_timeout_s: Annotated[
        float,
        Field(
            default=3500.0,
            ge=10.0,
            description=(
                "Per-call timeout in seconds for generate_content(). "
                "Set near Cloud Run max (3600s)."
            ),
        ),
    ]
    batch_result_timeout_s: Annotated[
        float,
        Field(
            default=3550.0,
            ge=10.0,
            description=(
                "Timeout in seconds for future.result() in _process_batches_parallel."
            ),
        ),
    ]


class BqSettings(BaseSettings):
    """
    Configuration settings for the BigQuery service.
    Loads from environment variables prefixed with ``SMAE_BQ_``.
    """

    model_config = SettingsConfigDict(env_prefix="SMAE_BQ_")

    project: Annotated[
        Optional[str],
        Field(
            default=None,
            description="GCP project for BigQuery writes; resolved from ADC when unset",
        ),
    ]
    dataset: Annotated[
        str,
        Field(
            default="nutrimental_information",
            description="BigQuery dataset containing the food equivalents table",
        ),
    ]
    table: Annotated[
        str,
        Field(default="food_equivalents", description="BigQuery table for food items"),
    ]
    dead_letter_table: Annotated[
        str,
        Field(
            default="food_equivalents_dead_letter",
            description="BigQuery dead-letter table for failed row inserts",
        ),
    ]
    batch_size: Annotated[
        int,
        Field(
            default=500,
            ge=1,
            description="Max rows per load_table_from_json batch job",
        ),
    ]
    job_timeout_s: Annotated[
        float,
        Field(
            default=300.0,
            ge=5.0,
            description="Timeout in seconds for BigQuery job.result() calls.",
        ),
    ]
