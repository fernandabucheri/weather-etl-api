import pytest
from etl.extract import WeatherExtractor


def test_extract_weather_data_success(mock_openweathermap_api):
    extractor = WeatherExtractor(api_key="fake")
    data = extractor.extract_weather_data("São Paulo")
    assert data["name"] == "São Paulo"


def test_extract_weather_data_failure_api_error(mock_openweathermap_api):
    extractor = WeatherExtractor(api_key="fake")
    data = extractor.extract_weather_data("CidadeInvalida")
    assert data is None