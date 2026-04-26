import flask
import functions_framework
from loguru import logger
from pydantic import ValidationError

from backend.smae_engine.source_code.pipeline import IngestionPipeline
from backend.smae_engine.source_code.schemas import ExtractionRequest


@functions_framework.http
def smae_handler(request: flask.Request) -> tuple[str, int]:
    """
    Cloud Functions v2 HTTP entry point for the SMAE ingestion pipeline.
    Parses the JSON body into an ExtractionRequest, runs the pipeline, and
    returns the serialized ExtractionResponse on success.

    Args:
        request: flask.Request -> Incoming HTTP request carrying a JSON body.

    Returns:
        tuple[str, int] -> (JSON body, HTTP status code).
    """
    logger.info("smae_handler invoked")
    try:
        payload = request.get_json(silent=True) or {}
        extraction_request = ExtractionRequest.model_validate(payload)
    except ValidationError as exc:
        logger.warning(f"Request validation failed: {exc.error_count()} error(s)")
        return flask.json.dumps({"error": "Invalid request payload"}), 400

    try:
        pipeline = IngestionPipeline()
        result = pipeline.run(extraction_request)
        return result.model_dump_json(), 200
    except Exception:
        logger.exception("Unhandled error in smae_handler")
        return flask.json.dumps({"error": "Internal server error"}), 500
