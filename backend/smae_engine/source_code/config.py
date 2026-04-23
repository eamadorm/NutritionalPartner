from typing import Annotated
from pydantic import Field
from pydantic_settings import BaseSettings


class SMAEConfig(BaseSettings):
    """Configuration for the SMAE Engine using Pydantic BaseSettings."""

    PROJECT_ID: Annotated[
        str, Field(description="GCP Project ID", default="nutritional-partner")
    ]
    LOCATION: Annotated[str, Field(description="GCP Location", default="us-central1")]

    DATASET_ID: Annotated[
        str, Field(description="BQ Dataset ID", default="nutrimental_information")
    ]
    TABLE_FOOD: Annotated[
        str, Field(description="Main food table name", default="food_equivalents")
    ]
    TABLE_DLQ: Annotated[
        str,
        Field(description="Dead letter table name", default="extraction_dead_letter"),
    ]

    MODEL_NAME: Annotated[
        str, Field(description="Gemini Model version", default="gemini-2.5-flash")
    ]

    class Config:
        env_prefix = "SMAE_"
