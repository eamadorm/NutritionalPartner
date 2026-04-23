from datetime import datetime
from typing import Optional, Annotated
from pydantic import BaseModel, Field
import uuid

# GCS URI Pattern: gs://bucket-name/path/to/file
GCS_URI_PATTERN = r"^gs://[a-z0-9_.-]+/.+"


class ExtractionRequest(BaseModel):
    """
    Request schema for SMAE extraction.
    """

    gcs_uri: Annotated[
        str,
        Field(
            description="GCS URI of the PDF (gs://bucket/path)", pattern=GCS_URI_PATTERN
        ),
    ]
    page_range: Annotated[
        Optional[tuple[int, int]],
        Field(description="Start and End page range (1-indexed)", default=None),
    ]
    specific_pages: Annotated[
        Optional[list[int]],
        Field(description="List of specific pages to process", default=None),
    ]


class FoodItem(BaseModel):
    """
    Schema for a single food item extracted from SMAE with validation constraints.
    """

    family_group: Annotated[
        str, Field(description="Nutritional family group", min_length=1)
    ]
    food: Annotated[str, Field(description="Name of the food item", min_length=1)]
    suggested_quantity: Annotated[
        str, Field(description="Suggested portion size", min_length=1)
    ]
    unit: Annotated[str, Field(description="Unit of measurement", min_length=1)]
    gross_weight_grams: Annotated[float, Field(description="Gross weight", ge=0)]
    net_weight_grams: Annotated[float, Field(description="Net edible weight", ge=0)]
    energy_kcal: Annotated[float, Field(description="Energy content", ge=0)]
    protein_grams: Annotated[float, Field(description="Protein content", ge=0)]
    lipids_grams: Annotated[float, Field(description="Total lipids content", ge=0)]
    carbohidrates_grams: Annotated[
        float, Field(description="Total carbohydrates content", ge=0)
    ]
    fiber_grams: Annotated[float, Field(description="Dietary fiber content", ge=0)]

    processed_at: Annotated[datetime, Field(description="Extraction timestamp (UTC)")]
    food_uuid: Annotated[
        Optional[str],
        Field(description="Deterministic unique identifier", default=None),
    ]
    source_uri: Annotated[
        Optional[str], Field(description="Source GCS URI", default=None)
    ]
    page_number: Annotated[
        Optional[int], Field(description="Page number", ge=1, default=None)
    ]
    is_active: Annotated[
        bool, Field(description="SCD Type 2 active flag", default=True)
    ]

    def generate_uuid(self, source_uri: str) -> None:
        """
        Generates a deterministic UUID based on food name and source.

        Args:
            source_uri: str -> The URI of the source document
        """
        namespace = uuid.NAMESPACE_DNS
        name = f"{source_uri}_{self.food}"
        self.food_uuid = str(uuid.uuid5(namespace, name))
        self.source_uri = source_uri


class DeadLetterRecord(BaseModel):
    """
    Schema for failed extractions with validation constraints.
    """

    source_uri: Annotated[
        str, Field(description="Source GCS URI", pattern=GCS_URI_PATTERN)
    ]
    page_number: Annotated[int, Field(description="Failed page number", ge=1)]
    error_message: Annotated[
        str, Field(description="Detailed error description", min_length=1)
    ]
    processed_at: Annotated[datetime, Field(description="Failure timestamp")]
    ingestion_at: Annotated[
        Optional[datetime], Field(description="BQ Ingestion timestamp", default=None)
    ]


class ExtractionMetadata(BaseModel):
    """
    Metadata for the extraction process.
    """

    total_items: Annotated[int, Field(description="Total food items extracted", ge=0)]
    processing_time_seconds: Annotated[
        float, Field(description="Total processing duration", ge=0)
    ]
    model_version: Annotated[
        str, Field(description="Gemini model used", default="gemini-2.5-flash")
    ]
    source_blob: Annotated[str, Field(description="Source GCS URI")]


class ExtractionResponse(BaseModel):
    """
    Unified response schema for the SMAE Engine.
    """

    items: Annotated[
        list[FoodItem], Field(description="List of successfully extracted items")
    ]
    dead_letter_items: Annotated[
        list[DeadLetterRecord], Field(description="List of failed extractions")
    ]
    metadata: Annotated[ExtractionMetadata, Field(description="Execution metadata")]
