import pytest
from etl.transform import WeatherTransformer


def test_add_derived_fields(sample_transformed_data):
    transformer = WeatherTransformer()
    result = transformer.add_derived_fields(sample_transformed_data)
    assert "heat_index" in result
    assert result["heat_index"] == pytest.approx(33.0)
