import threading
from typing import Optional

from google.cloud import storage
from loguru import logger

from backend.smae_engine.source_code.config import GcsSettings
from backend.smae_engine.source_code.gcs_service.schemas import GcsDownloadResult

_DEFAULT_MIME_TYPE = "application/pdf"


class GcsService:
    """
    Encapsulates all Google Cloud Storage interactions for the SMAE pipeline.
    Handles bucket validation, MIME type resolution, and resilient PDF downloads.
    """

    def __init__(self, settings: GcsSettings) -> None:
        self._settings = settings
        self._client: Optional[storage.Client] = None
        self._lock = threading.Lock()

    def validate_trusted_bucket(self, gcs_uri: str) -> None:
        """
        Raises ValueError if the URI targets a bucket other than the configured trusted one.

        Args:
            gcs_uri: str -> GCS URI to validate (gs://bucket/path.pdf).
        """
        bucket_name = gcs_uri.removeprefix("gs://").partition("/")[0]
        if bucket_name != self._settings.trusted_bucket:
            raise ValueError(f"Untrusted bucket: {bucket_name}")

    def get_mime_type(self, gcs_uri: str) -> str:
        """
        Fetches the MIME type from GCS blob metadata; validates file size; falls back to default.

        Args:
            gcs_uri: str -> GCS URI of the target blob.

        Returns:
            str -> MIME type string for use in Gemini API calls.
        """
        path = gcs_uri.removeprefix("gs://")
        bucket_name, _, blob_name = path.partition("/")
        client = self._build_client()
        blob = client.bucket(bucket_name).get_blob(blob_name)
        if blob:
            max_bytes = self._settings.max_file_size_mb * 1024 * 1024
            if blob.size > max_bytes:
                raise ValueError(
                    f"File exceeds maximum size of {self._settings.max_file_size_mb} MB"
                )
            if blob.content_type:
                logger.debug(f"MIME type from metadata: {blob.content_type}")
                return blob.content_type
        logger.debug(
            f"No MIME type in metadata for bucket: {bucket_name}, using default."
        )
        return _DEFAULT_MIME_TYPE

    def download_pdf(self, gcs_uri: str) -> GcsDownloadResult:
        """
        Downloads the source PDF from GCS after validating its size.
        Uses generation pinning to avoid reading a concurrently modified blob.

        Args:
            gcs_uri: str -> GCS URI of the PDF to download.

        Returns:
            GcsDownloadResult -> Raw PDF bytes and resolved blob size.
        """
        path = gcs_uri.removeprefix("gs://")
        bucket_name, _, blob_name = path.partition("/")
        client = self._build_client()
        blob = client.bucket(bucket_name).blob(blob_name)
        blob.reload()
        max_bytes = self._settings.max_source_pdf_size_mb * 1024 * 1024
        if blob.size is None or blob.size > max_bytes:
            raise ValueError(
                f"Source PDF exceeds {self._settings.max_source_pdf_size_mb} MB"
            )
        logger.debug(
            f"Downloading {blob.size / (1024 * 1024):.1f} MB from bucket: {bucket_name}"
        )
        pinned_blob = client.bucket(bucket_name).blob(
            blob_name, generation=blob.generation
        )
        pdf_bytes = pinned_blob.download_as_bytes()
        if len(pdf_bytes) > max_bytes:
            raise ValueError(
                f"Source PDF exceeds {self._settings.max_source_pdf_size_mb} MB"
            )
        return GcsDownloadResult(pdf_bytes=pdf_bytes, size_bytes=len(pdf_bytes))

    def _build_client(self) -> storage.Client:
        """Initializes (and caches) the GCS Storage client using ADC."""
        if self._client is None:
            with self._lock:
                if self._client is None:
                    self._client = storage.Client()
        return self._client
