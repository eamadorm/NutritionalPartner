import re
from datetime import datetime, timezone
from typing import Annotated, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


_GCS_URI_PATTERN = re.compile(r"^gs://[a-z0-9][a-z0-9._-]{1,61}[a-z0-9]/.+\.pdf$")


class ExtractionRequest(BaseModel):
    """
    Request model for the SMAE extraction engine.
    """

    gcs_uri: Annotated[str, Field(description="The GCS URI of the SMAE PDF document")]
    page_range: Annotated[
        Optional[tuple[int, int]],
        Field(default=None, description="Inclusive page range (start, end), 1-indexed"),
    ]
    pages: Annotated[
        Optional[list[int]],
        Field(
            default=None,
            max_length=2000,
            description="Specific 1-indexed page numbers to process",
        ),
    ]

    @field_validator("gcs_uri")
    @classmethod
    def validate_gcs_uri(cls, v: str) -> str:
        if not _GCS_URI_PATTERN.fullmatch(v):
            raise ValueError("gcs_uri must match gs://<bucket>/<path>.pdf")
        return v

    @field_validator("page_range")
    @classmethod
    def validate_page_range(
        cls, v: Optional[tuple[int, int]]
    ) -> Optional[tuple[int, int]]:
        if v is None:
            return v
        start, end = v
        if start < 1:
            raise ValueError("page_range start must be >= 1")
        if end < start:
            raise ValueError("page_range end must be >= start")
        if end - start + 1 > 2000:
            raise ValueError("page_range cannot span more than 2000 pages")
        return v

    @field_validator("pages")
    @classmethod
    def validate_pages_list(cls, v: Optional[list[int]]) -> Optional[list[int]]:
        if v is None:
            return v
        if not v:
            raise ValueError("pages list cannot be empty")
        if any(p < 1 for p in v):
            raise ValueError("all page numbers must be >= 1")
        return sorted(set(v))

    @model_validator(mode="after")
    def validate_page_selection_exclusivity(self) -> "ExtractionRequest":
        if self.page_range is not None and self.pages is not None:
            raise ValueError("Cannot specify both page_range and pages simultaneously")
        return self


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
    status: Annotated[str, Field(description="Validation result status")]
    items_count: Annotated[int, Field(description="Number of validated items", ge=0)]
