import os
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
    logger.info("SMAE handler invoked")
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


if __name__ == "__main__":
    # Local development entry point
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
