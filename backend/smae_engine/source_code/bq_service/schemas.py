from typing import Annotated

from pydantic import BaseModel, Field

from backend.smae_engine.source_code.gemini_service.schemas import FoodItem


class FoodEquivalentRow(FoodItem):
    """
    BigQuery row schema for the food_equivalents table.
    Extends FoodItem with source traceability and SCD Type 2 lifecycle fields.
    """

    source_uri: Annotated[
        str,
        Field(description="GCS URI of the originating PDF document"),
    ]
    active: Annotated[
        bool,
        Field(
            description="SCD Type 2 flag; False when superseded by a newer ingestion",
            default=True,
        ),
    ]


class LoadResponse(BaseModel):
    """
    Result of the BigQuery load step in the IngestionPipeline.
    """

    rows_inserted: Annotated[
        int,
        Field(description="Rows successfully written to food_equivalents", ge=0),
    ]
    rows_failed: Annotated[
        int,
        Field(description="Rows that could not be written to the main table", ge=0),
    ]
    dead_letter_rows: Annotated[
        int,
        Field(description="Rows routed to the dead-letter table", ge=0),
    ]
