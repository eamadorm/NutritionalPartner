import json
import uuid
from datetime import datetime, timezone

from google import genai
from google.genai import types
from loguru import logger
from pydantic import ValidationError

from backend.smae_engine.source_code.schemas import (
    ExtractionMetadata,
    ExtractionRequest,
    ExtractionResponse,
    FoodItem,
)

NAMESPACE_URL = uuid.NAMESPACE_URL


def _generate_food_uuid(source_uri: str, food_name: str) -> str:
    """
    Generates a deterministic UUID based on the source URI and food name.

    Args:
        source_uri: str -> The URI of the source document
        food_name: str -> The name of the food item

    Returns:
        str -> The generated UUID5 string
    """
    name_str = f"{source_uri}_{food_name}"
    return str(uuid.uuid5(NAMESPACE_URL, name_str))


def process_document(request: ExtractionRequest) -> ExtractionResponse:
    """
    Processes a document using the Google GenAI SDK to extract FoodItems.

    Args:
        request: ExtractionRequest -> The request containing the GCS URI.

    Returns:
        ExtractionResponse -> The response containing the extracted items and metadata.
    """
    logger.info(f"Starting processing for URI: {request.gcs_uri}")

    import google.auth

    _, project_id = google.auth.default()

    # Initialize the genai client for Vertex AI to use ADC instead of API keys
    client = genai.Client(vertexai=True, project=project_id, location="us-central1")

    try:
        file_part = types.Part.from_uri(
            file_uri=request.gcs_uri, mime_type="application/pdf"
        )

        prompt = (
            "You are an expert nutritional data extractor. "
            "Extract all the food items from the provided document into a structured list. "
            "Make sure to extract all columns accurately based on the PDF tables. "
            "If a value is not present, use null. "
            "Leave the `food_uuid` as 'temp' and `ingested_at` as the current time."
        )

        logger.debug(f"Calling Gemini for: {request.gcs_uri}")

        # Pydantic schema validation is automatically handled by the SDK
        result = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[file_part, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=list[FoodItem],
            ),
        )

        extracted_data = json.loads(result.text)

        now = datetime.now(timezone.utc)
        final_items = []
        for item_data in extracted_data:
            item_data["food_uuid"] = _generate_food_uuid(
                request.gcs_uri, item_data.get("food") or "unknown"
            )
            # Need to format datetime as string or pass datetime object
            item_data["ingested_at"] = now.isoformat()

            # Validates against Pydantic schema
            food_item = FoodItem(**item_data)
            final_items.append(food_item)

        logger.info(f"Successfully extracted {len(final_items)} items.")

        metadata = ExtractionMetadata(source_uri=request.gcs_uri, processed_at=now)

        response = ExtractionResponse(items=final_items, metadata=metadata)
        verify_extraction(response)

        return response
    except ValidationError as ve:
        logger.error(f"Validation error during extraction: {ve}")
        raise
    except Exception as e:
        logger.error(f"Error processing document {request.gcs_uri}: {e}")
        raise


def verify_extraction(response: ExtractionResponse) -> dict:
    """
    Verifies the structural integrity and logic of the extraction response.

    Args:
        response: ExtractionResponse -> The completed extraction response.

    Returns:
        dict -> Status dictionary of the verification.
    """
    logger.debug("Verifying extraction response...")

    for item in response.items:
        if item.energy_kcal is not None and item.energy_kcal < 0:
            raise ValueError(f"Energy cannot be negative: {item.energy_kcal}")
        if item.protein_g is not None and item.protein_g < 0:
            raise ValueError(f"Protein cannot be negative: {item.protein_g}")

    return {"status": "valid", "items_count": len(response.items)}


if __name__ == "__main__":
    # Example usage
    request = ExtractionRequest(gcs_uri="gs://nutritional-data-sources/sample.pdf")
    # In a real run, ADC would need to be set up.
    # process_document(request)
