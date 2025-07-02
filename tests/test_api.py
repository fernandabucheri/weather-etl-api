import pytest
from unittest.mock import patch
from datetime import datetime

def test_get_latest_weather_not_found(client, weather_loader_mocked_db):
    with patch.object(weather_loader_mocked_db, "get_latest_data", return_value=None):
        with patch("api.main.get_weather_loader", return_value=weather_loader_mocked_db):
            response = client.get("/weather/latest?city=Inexistente")
            assert response.status_code == 404


def test_get_weather_by_city_success(client, weather_loader_mocked_db, sample_transformed_data):
    with patch.object(weather_loader_mocked_db, "get_data_by_city", return_value=[sample_transformed_data]):
        with patch("api.main.get_weather_loader", return_value=weather_loader_mocked_db):
            response = client.get("/weather/by_city?city=São Paulo")
            assert response.status_code == 200
            assert response.json()[0]["city_name"] == "São Paulo"


def test_get_weather_by_city_not_found(client, weather_loader_mocked_db):
    with patch.object(weather_loader_mocked_db, "get_data_by_city", return_value=[]):
        with patch("api.main.get_weather_loader", return_value=weather_loader_mocked_db):
            response = client.get("/weather/by_city?city=Inexistente")
            assert response.status_code == 404


def test_get_available_cities_success(client, weather_loader_mocked_db):
    mock_cursor = weather_loader_mocked_db.connection.cursor.return_value
    mock_cursor.fetchall.return_value = [("São Paulo",), ("Rio de Janeiro",)]

    with patch("api.main.get_weather_loader", return_value=weather_loader_mocked_db):
        response = client.get("/weather/cities")
        assert response.status_code == 200
        assert "São Paulo" in response.json()


def test_get_weather_stats_success(client, weather_loader_mocked_db):
    mock_cursor = weather_loader_mocked_db.connection.cursor.return_value
    mock_cursor.fetchone.return_value = (10, 2, datetime.now(), datetime.now(), 25.0, 20.0, 30.0, 60.0)
