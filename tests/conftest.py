import os
import sys
from unittest.mock import MagicMock, patch

import pytest
import requests
from dotenv import load_dotenv
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.main import app
from etl.load import WeatherLoader


@pytest.fixture(scope="session", autouse=True)
def load_env():
    """Carrega variáveis de ambiente do .env"""
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


@pytest.fixture
def client():
    """TestClient para FastAPI"""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_openweathermap_api():
    """Mock da requests.get para API externa"""
    def mock_response(url, params, timeout=10):
        city = params.get("q", "").split(",")[0]
        if city == "São Paulo":
            data = {"name": "São Paulo", "main": {"temp": 25.5}, "cod": 200}
            mock = MagicMock()
            mock.status_code = 200
            mock.json.return_value = data
            mock.raise_for_status.return_value = None
            return mock
        else:
            mock = MagicMock()
            mock.status_code = 401
            mock.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Client Error")
            return mock

    with patch("requests.get", side_effect=mock_response) as mock_get:
        yield mock_get


@pytest.fixture
def mock_db_connection():
    """Mock da conexão com banco"""
    with patch("psycopg2.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        yield mock_conn


@pytest.fixture
def weather_loader_mocked_db():
    """Instância mockada de WeatherLoader"""
    loader = WeatherLoader({
        "host": "localhost",
        "port": "5432",
        "database": "test",
        "user": "user",
        "password": "pass"
    })
    loader.connection = MagicMock()
    loader.connection.cursor.return_value = MagicMock()
    return loader


@pytest.fixture
def sample_transformed_data():
    return {
        "city_name": "São Paulo",
        "temperature": 25.5,
        "data_timestamp": "2024-01-01T10:00:00",
        "processed_at": "2024-01-01T10:10:00",
        "humidity": 65,
        "heat_index": 33.0,
        "temperature_category": "Quente",
        "humidity_category": "Moderada"
    }
