import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from backend.smae_engine.source_code.schemas import (
    ExtractionMetadata,
    ExtractionResponse,
    FoodItem,
)
from backend.smae_engine.source_code.main import verify_extraction, _generate_food_uuid


def test_generate_food_uuid_happy_path():
    """Test deterministic UUID generation."""
    uuid1 = _generate_food_uuid("gs://test.pdf", "Apple")
    uuid2 = _generate_food_uuid("gs://test.pdf", "Apple")
    assert uuid1 == uuid2


def test_generate_food_uuid_edge_cases():
    """Test different inputs yield different UUIDs."""
    uuid1 = _generate_food_uuid("gs://test.pdf", "Apple")
    uuid2 = _generate_food_uuid("gs://test.pdf", "Banana")
    assert uuid1 != uuid2


def test_verify_extraction_happy_path():
    """Test verification passes for valid data."""
    metadata = ExtractionMetadata(
        source_uri="gs://test", processed_at=datetime.now(timezone.utc)
    )
    item = FoodItem(
        food_uuid="test-uuid",
        food="Apple",
        energy_kcal=50,
        protein_g=0.3,
        ingested_at=datetime.now(timezone.utc),
    )
    response = ExtractionResponse(items=[item], metadata=metadata)

    result = verify_extraction(response)
    assert result["status"] == "valid"
    assert result["items_count"] == 1


def test_verify_extraction_failure_modes():
    """Test Pydantic numeric validations reject negative values."""
    with pytest.raises(ValidationError) as excinfo:
        FoodItem(
            food_uuid="test-uuid",
            food="Apple",
            energy_kcal=-10,  # Negative energy should fail
            ingested_at=datetime.now(timezone.utc),
        )
    assert "Input should be greater than or equal to 0" in str(excinfo.value)

    with pytest.raises(ValidationError) as excinfo:
        FoodItem(
            food_uuid="test-uuid",
            food="Apple",
            protein_g=-1.5,  # Negative protein should fail
            ingested_at=datetime.now(timezone.utc),
        )
    assert "Input should be greater than or equal to 0" in str(excinfo.value)


def test_verify_extraction_edge_cases():
    """Test verification works with empty lists and nulls."""
    metadata = ExtractionMetadata(
        source_uri="gs://test", processed_at=datetime.now(timezone.utc)
    )
    response = ExtractionResponse(items=[], metadata=metadata)

    result = verify_extraction(response)
    assert result["status"] == "valid"
    assert result["items_count"] == 0

    item_nulls = FoodItem(
        food_uuid="test-uuid",
        ingested_at=datetime.now(timezone.utc),
        # All other fields default to None, which is valid and handled correctly.
    )
    response2 = ExtractionResponse(items=[item_nulls], metadata=metadata)
    assert verify_extraction(response2)["status"] == "valid"
