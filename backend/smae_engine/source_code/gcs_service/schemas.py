from typing import Annotated

from pydantic import BaseModel, Field


class GcsDownloadResult(BaseModel):
    """
    Result of downloading a PDF blob from GCS.
    Carries the raw bytes and the resolved generation for pinned reads.
    """

    pdf_bytes: Annotated[
        bytes,
        Field(description="Raw bytes of the downloaded PDF"),
    ]
    size_bytes: Annotated[
        int,
        Field(description="Size of the blob at download time", ge=0),
    ]
