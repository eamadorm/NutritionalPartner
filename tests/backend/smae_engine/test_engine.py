import pytest
from unittest.mock import MagicMock, patch
from backend.smae_engine.source_code.main import SMAEEngine
from backend.smae_engine.source_code.schemas import FoodItem

from datetime import datetime, timezone


@pytest.fixture
def mock_engine():
    with (
        patch("backend.smae_engine.source_code.main.vertexai.init"),
        patch("backend.smae_engine.source_code.main.storage.Client"),
        patch("backend.smae_engine.source_code.main.bigquery.Client"),
        patch("backend.smae_engine.source_code.main.GenerativeModel"),
    ):
        yield SMAEEngine()


def test_generate_food_uuid_consistency():
    """Verify that UUID generation is deterministic based on food name and family group."""
    item_data = {
        "family_group": "Fruit",
        "food": "Apple",
        "suggested_quantity": "1",
        "unit": "piece",
        "energy_kcal": 52,
        "gross_weight_grams": 100,
        "net_weight_grams": 90,
        "protein_grams": 0,
        "lipids_grams": 0,
        "carbohidrates_grams": 14,
        "fiber_grams": 2,
        "page_number": 1,
        "processed_at": datetime.now(timezone.utc),
    }
    item1 = FoodItem(**item_data)
    item2 = FoodItem(**item_data)

    item1.generate_uuid("gs://test/source.pdf")
    item2.generate_uuid("gs://test/source.pdf")

    assert item1.food_uuid == item2.food_uuid

    # Change name should change UUID
    item_data["food"] = "Pear"
    item3 = FoodItem(**item_data)
    item3.generate_uuid("gs://test/source.pdf")
    assert item1.food_uuid != item3.food_uuid


def test_page_parsing_failure_raises_exception(mock_engine):
    """Verify that a page parsing error propagates (the run method handles logging)."""
    # Mocking a failed extraction
    mock_engine.model.generate_content.side_effect = Exception("API Error")

    with pytest.raises(Exception):
        mock_engine._process_page("gs://test/file.pdf", 1, "gs://test/source.pdf")


def test_successful_extraction_returns_items(mock_engine):
    """Verify that a successful extraction returns validated FoodItem objects."""
    mock_response = MagicMock()
    mock_response.text = '{"family_group": "Vegetables", "food": "Carrot", "suggested_quantity": "1", "unit": "cup", "gross_weight_grams": 100, "net_weight_grams": 90, "energy_kcal": 40, "protein_grams": 1, "lipids_grams": 0, "carbohidrates_grams": 10, "fiber_grams": 2}'

    # The response is actually a list of JSON items
    mock_response.text = "[" + mock_response.text + "]"
    mock_engine.model.generate_content.return_value = mock_response

    items = mock_engine._process_page("gs://test/file.pdf", 1, "gs://test/source.pdf")
    assert len(items) == 1
    assert items[0].food == "Carrot"
    assert items[0].food_uuid is not None
