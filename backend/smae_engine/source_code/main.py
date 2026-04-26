import os
import sys
import uvicorn
from fastapi import FastAPI, HTTPException
from loguru import logger

from backend.smae_engine.source_code.pipeline import IngestionPipeline
from backend.smae_engine.source_code.schemas import (
    ExtractionRequest,
    ExtractionResponse,
)

# Initialize FastAPI app
app = FastAPI(
    title="SMAE Ingestion Engine",
    description="Vertex AI powered nutritional PDF extraction pipeline",
    version="1.0.0",
)


@app.post("/", response_model=ExtractionResponse)
async def smae_handler(request: ExtractionRequest) -> ExtractionResponse:
    """
    HTTP POST entry point for the SMAE ingestion pipeline.
    Parses the JSON body into an ExtractionRequest and runs the orchestrator.

    Args:
       request: ExtractionRequest -> Validated request with GCS URI and optional page params.

    Returns:
        ExtractionResponse -> Validated response containing items and metadata.
    """
    logger.info("SMAE handler invoked via HTTP")
    try:
        pipeline = IngestionPipeline()
        # FastAPI handles model validation and serialization automatically
        result = pipeline.run(request)
        return result
    except Exception:
        logger.exception("Unhandled error in smae_handler")
        raise HTTPException(status_code=500, detail="Internal server error")


def run_cli() -> None:
    """
    CLI entry point for local execution or batch jobs.
    Takes a GCS URI as a positional argument and prints the JSON result.

    Args:
       None -> Uses sys.argv for positional GCS URI.

    Returns:
        None -> Prints result to stdout or exits with code 1.
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
        # Local development server
        port = int(os.environ.get("PORT", 8080))
        uvicorn.run(app, host="0.0.0.0", port=port)
