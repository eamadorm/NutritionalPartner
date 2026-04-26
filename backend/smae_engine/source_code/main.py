import os
import sys
from flask import Flask, request, jsonify
from loguru import logger
from pydantic import ValidationError

from backend.smae_engine.source_code.pipeline import IngestionPipeline
from backend.smae_engine.source_code.schemas import ExtractionRequest

# Initialize Flask app
app = Flask(__name__)


@app.route("/", methods=["POST"])
def smae_handler():
    """
    HTTP entry point for the SMAE ingestion pipeline.
    Parses the JSON body into an ExtractionRequest, runs the pipeline, and
    returns the serialized ExtractionResponse on success.

    Returns:
        Response -> JSON body and HTTP status code.
    """
    logger.info("SMAE handler invoked via HTTP")
    try:
        payload = request.get_json(silent=True) or {}
        extraction_request = ExtractionRequest.model_validate(payload)
    except ValidationError as exc:
        logger.warning(f"Request validation failed: {exc.error_count()} error(s)")
        return jsonify(
            {"error": "Invalid request payload", "details": exc.errors()}
        ), 400

    try:
        pipeline = IngestionPipeline()
        result = pipeline.run(extraction_request)
        return result.model_dump_json(), 200, {"Content-Type": "application/json"}
    except Exception:
        logger.exception("Unhandled error in smae_handler")
        return jsonify({"error": "Internal server error"}), 500


def run_cli():
    """
    CLI entry point for local execution or batch jobs.
    Usage: python -m backend.smae_engine.source_code.main gs://bucket/file.pdf
    """
    if len(sys.argv) < 2:
        print("Usage: python -m backend.smae_engine.source_code.main <gcs_uri>")
        sys.exit(1)

    gcs_uri = sys.argv[1]
    logger.info(f"Running SMAE pipeline via CLI for: {gcs_uri}")

    try:
        request_obj = ExtractionRequest(gcs_uri=gcs_uri)
        pipeline = IngestionPipeline()
        result = pipeline.run(request_obj)
        print(result.model_dump_json(indent=2))
    except Exception as exc:
        logger.error(f"CLI execution failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    # If a GCS URI is passed as an argument, run as CLI. Otherwise, run as server.
    if len(sys.argv) > 1 and sys.argv[1].startswith("gs://"):
        run_cli()
    else:
        # Local development server (SECURITY: debug=False for production readiness)
        port = int(os.environ.get("PORT", 8080))
        app.run(host="0.0.0.0", port=port, debug=False)
