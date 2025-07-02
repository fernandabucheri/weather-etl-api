"""
Módulo de extração de dados da API OpenWeatherMap
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WeatherExtractor:
    """Classe responsável pela extração de dados meteorológicos"""

    def __init__(self, api_key: str):
        """
        Inicializa o extrator com a chave da API

        Args:
            api_key (str): Chave da API OpenWeatherMap
        """
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"

    def extract_weather_data(
        self, city: str, country_code: str = "BR"
    ) -> Optional[Dict[str, Any]]:
        """
        Extrai dados meteorológicos para uma cidade específica

        Args:
            city (str): Nome da cidade
            country_code (str): Código do país (padrão: BR)

        Returns:
            Dict[str, Any]: Dados meteorológicos ou None em caso de erro
        """
        try:
            # Parâmetros da requisição
            params = {
                "q": f"{city},{country_code}",
                "appid": self.api_key,
                "units": "metric",  # Celsius
                "lang": "pt_br",
            }

            logger.info(f"Extraindo dados meteorológicos para {city}, {country_code}")

            # Fazer requisição para a API
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()

            # Converter resposta para JSON
            weather_data = response.json()

            # Adicionar timestamp da extração
            weather_data["extracted_at"] = datetime.now(timezone.utc).isoformat()

            logger.info(f"Dados extraídos com sucesso para {city}")
            return weather_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição para {city}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON para {city}: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao extrair dados para {city}: {e}")
            return None

    def extract_multiple_cities(self, cities: list) -> Dict[str, Any]:
        """
        Extrai dados meteorológicos para múltiplas cidades

        Args:
            cities (list): Lista de cidades

        Returns:
            Dict[str, Any]: Dados de todas as cidades
        """
        results = {}

        for city in cities:
            data = self.extract_weather_data(city)
            if data:
                results[city] = data
            else:
                logger.warning(f"Falha ao extrair dados para {city}")

        return results


def main():
    """Função principal para teste do módulo"""

    api_key = os.getenv("OPENWEATHER_API_KEY", "")

    if api_key == "":
        logger.warning(
            "Atenção! Configure OPENWEATHER_API_KEY para usar uma chave válida."
        )

    # Criar extrator
    extractor = WeatherExtractor(api_key)

    # Testar extração para São Paulo
    data = extractor.extract_weather_data("São Paulo")

    if data:
        print("Dados extraídos com sucesso:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print("Falha na extração de dados")


if __name__ == "__main__":
    main()
