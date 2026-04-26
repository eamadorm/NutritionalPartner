from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, Field


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
        Field(
            description="The group of food, e.g., 'VEGETABLES'",
            default=None,
            max_length=100,
        ),
    ]
    food: Annotated[
        Optional[str],
        Field(
            description="The name of the specific food item",
            default=None,
            max_length=200,
        ),
    ]
    suggested_quantity: Annotated[
        Optional[str],
        Field(
            description="The suggested quantity (may include fractions or strings)",
            default=None,
            max_length=50,
        ),
    ]
    unit: Annotated[
        Optional[str],
        Field(
            description="The unit of measurement",
            default=None,
            max_length=50,
        ),
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


class ExtractResponse(BaseModel):
    """
    Intermediate response carrying raw items returned by Gemini extraction
    along with the source URI required for downstream transformation.
    """

    raw_items: Annotated[
        list[dict[str, object]],
        Field(description="Raw items from Gemini response"),
    ]
    source_uri: Annotated[
        str,
        Field(description="Source GCS URI passed through from the request"),
    ]


class TransformResponse(BaseModel):
    """
    Intermediate response containing the validated and enriched FoodItem
    models produced by the transform step of the pipeline.
    """

    items: Annotated[
        list[FoodItem],
        Field(description="Validated and enriched FoodItem models"),
    ]


class VerificationResponse(BaseModel):
    """
    Result of the structural integrity check on an extraction response.
    """

    status: Annotated[str, Field(description="Validation result status")]
    items_count: Annotated[int, Field(description="Number of validated items", ge=0)]
