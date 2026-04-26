import re
from datetime import datetime, timezone
from typing import Annotated, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# Re-export service schemas so existing callers keep working without changes.
from backend.smae_engine.source_code.bq_service.schemas import (  # noqa: F401
    FoodEquivalentRow,
    LoadResponse,
)
from backend.smae_engine.source_code.gemini_service.schemas import (  # noqa: F401
    ExtractResponse,
    FoodItem,
    TransformResponse,
    VerificationResponse,
)

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
