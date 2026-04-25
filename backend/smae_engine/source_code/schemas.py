from datetime import datetime, timezone
from typing import Annotated, Optional

from pydantic import BaseModel, Field


class ExtractionRequest(BaseModel):
    """
    Request model for the SMAE extraction engine.
    """

    gcs_uri: Annotated[str, Field(description="The GCS URI of the SMAE PDF document")]


class FoodItem(BaseModel):
    """
    Schema representing a single food item extracted from the SMAE document.
    """

    food_uuid: Annotated[
        str,
        Field(
            description="Deterministic UUID generated using uuid5(source_uri + food_name)"
        ),
    ]
    food_group: Annotated[
        Optional[str],
        Field(description="The group of food, e.g., 'VEGETABLES'", default=None),
    ]
    food: Annotated[
        Optional[str],
        Field(description="The name of the specific food item", default=None),
    ]
    suggested_quantity: Annotated[
        Optional[str],
        Field(
            description="The suggested quantity (may include fractions or strings)",
            default=None,
        ),
    ]
    unit: Annotated[
        Optional[str], Field(description="The unit of measurement", default=None)
    ]
    gross_weight_rounded_g: Annotated[
        Optional[int],
        Field(description="The rounded gross weight in grams", ge=0, default=None),
    ]
    net_weight_g: Annotated[
        Optional[int], Field(description="The net weight in grams", ge=0, default=None)
    ]
    energy_kcal: Annotated[
        Optional[int],
        Field(description="The energy content in kilocalories", ge=0, default=None),
    ]
    protein_g: Annotated[
        Optional[float],
        Field(description="The protein content in grams", ge=0.0, default=None),
    ]
    lipids_g: Annotated[
        Optional[float],
        Field(description="The lipids (fats) content in grams", ge=0.0, default=None),
    ]
    carbohydrates_g: Annotated[
        Optional[float],
        Field(description="The carbohydrates content in grams", ge=0.0, default=None),
    ]
    ingested_at: Annotated[
        datetime, Field(description="Timestamp in UTC when the row was created")
    ]


class ExtractionMetadata(BaseModel):
    """
    Metadata about the extraction process.
    """

    source_uri: Annotated[
        str, Field(description="The original GCS URI of the document")
    ]
    processed_at: Annotated[
        datetime,
        Field(
            description="When the document was processed",
            default_factory=lambda: datetime.now(timezone.utc),
        ),
    ]


class ExtractionResponse(BaseModel):
    """
    Response model containing extracted items and metadata.
    """

    items: Annotated[list[FoodItem], Field(description="List of extracted food items")]
    metadata: Annotated[ExtractionMetadata, Field(description="Extraction metadata")]
