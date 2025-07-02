import pytest
from etl.load import WeatherLoader
from unittest.mock import patch, MagicMock
import psycopg2


def test_connect_success(mock_db_connection):
    config = {"host": "localhost", "port": "5432", "database": "test", "user": "user", "password": "pass"}
    loader = WeatherLoader(config)
    loader.connect()
    assert loader.connection is not None


def test_disconnect(weather_loader_mocked_db):
    loader = weather_loader_mocked_db
    loader.disconnect()
    loader.connection.close.assert_called()


def test_load_weather_data_success(weather_loader_mocked_db, sample_transformed_data):
    loader = weather_loader_mocked_db
    result = loader.load_weather_data(sample_transformed_data)
    assert result is True
