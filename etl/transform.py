"""
Módulo de transformação de dados meteorológicos
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WeatherTransformer:
    """Classe responsável pela transformação de dados meteorológicos"""

    def __init__(self):
        """Inicializa o transformador"""
        pass

    def transform_weather_data(
        self, raw_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Transforma dados brutos da API em formato padronizado

        Args:
            raw_data (Dict[str, Any]): Dados brutos da API

        Returns:
            Dict[str, Any]: Dados transformados ou None em caso de erro
        """
        try:
            if not raw_data or "main" not in raw_data:
                logger.error("Dados inválidos para transformação")
                return None

            # Extrair informações principais
            main_data = raw_data.get("main", {})
            weather_data = raw_data.get("weather", [{}])[0]
            wind_data = raw_data.get("wind", {})
            clouds_data = raw_data.get("clouds", {})
            sys_data = raw_data.get("sys", {})
            coord_data = raw_data.get("coord", {})

            # Criar estrutura transformada
            transformed_data = {
                # Identificação
                "city_id": raw_data.get("id"),
                "city_name": raw_data.get("name"),
                "country_code": sys_data.get("country"),
                # Coordenadas
                "latitude": coord_data.get("lat"),
                "longitude": coord_data.get("lon"),
                # Dados meteorológicos principais
                "temperature": main_data.get("temp"),
                "temperature_feels_like": main_data.get("feels_like"),
                "temperature_min": main_data.get("temp_min"),
                "temperature_max": main_data.get("temp_max"),
                "pressure": main_data.get("pressure"),
                "humidity": main_data.get("humidity"),
                "sea_level_pressure": main_data.get("sea_level"),
                "ground_level_pressure": main_data.get("grnd_level"),
                # Condições meteorológicas
                "weather_main": weather_data.get("main"),
                "weather_description": weather_data.get("description"),
                "weather_icon": weather_data.get("icon"),
                # Vento
                "wind_speed": wind_data.get("speed"),
                "wind_direction": wind_data.get("deg"),
                "wind_gust": wind_data.get("gust"),
                # Nuvens
                "cloudiness": clouds_data.get("all"),
                # Visibilidade
                "visibility": raw_data.get("visibility"),
                # Timestamps
                "data_timestamp": datetime.fromtimestamp(
                    raw_data.get("dt", 0)
                ).isoformat(),
                "sunrise": (
                    datetime.fromtimestamp(sys_data.get("sunrise", 0)).isoformat()
                    if sys_data.get("sunrise")
                    else None
                ),
                "sunset": (
                    datetime.fromtimestamp(sys_data.get("sunset", 0)).isoformat()
                    if sys_data.get("sunset")
                    else None
                ),
                "extracted_at": raw_data.get("extracted_at"),
                "processed_at": datetime.now(timezone.utc).isoformat(),
                # Timezone
                "timezone_offset": raw_data.get("timezone"),
            }

            # Validar dados essenciais
            if not self._validate_transformed_data(transformed_data):
                logger.error("Dados transformados falharam na validação")
                return None

            logger.info(
                f"Dados transformados com sucesso para {transformed_data['city_name']}"
            )
            return transformed_data

        except Exception as e:
            logger.error(f"Erro ao transformar dados: {e}")
            return None

    def _validate_transformed_data(self, data: Dict[str, Any]) -> bool:
        """
        Valida se os dados transformados contêm informações essenciais

        Args:
            data (Dict[str, Any]): Dados transformados

        Returns:
            bool: True se válidos, False caso contrário
        """
        required_fields = [
            "city_name",
            "country_code",
            "temperature",
            "humidity",
            "pressure",
            "weather_main",
        ]

        for field in required_fields:
            if data.get(field) is None:
                logger.warning(f"Campo obrigatório ausente: {field}")
                return False

        # Validar ranges de valores
        if not (-100 <= data.get("temperature", 0) <= 60):
            logger.warning(
                f"Temperatura fora do range esperado: {data.get('temperature')}"
            )
            return False

        if not (0 <= data.get("humidity", 0) <= 100):
            logger.warning(f"Umidade fora do range esperado: {data.get('humidity')}")
            return False

        return True

    def normalize_city_name(self, city_name: str) -> str:
        """
        Normaliza nome da cidade

        Args:
            city_name (str): Nome da cidade

        Returns:
            str: Nome normalizado
        """
        if not city_name:
            return ""

        # Remover espaços extras e capitalizar
        normalized = city_name.strip().title()

        # Tratar casos especiais
        replacements = {
            "Sao Paulo": "São Paulo",
            "Rio De Janeiro": "Rio de Janeiro",
            "Belo Horizonte": "Belo Horizonte",
        }

        return replacements.get(normalized, normalized)

    def add_derived_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adiciona campos derivados aos dados

        Args:
            data (Dict[str, Any]): Dados transformados

        Returns:
            Dict[str, Any]: Dados com campos derivados
        """
        try:
            # Calcular índice de conforto térmico (simplificado)
            temp = data.get("temperature", 0)
            humidity = data.get("humidity", 0)

            if temp and humidity:
                # Fórmula simplificada de índice de calor
                heat_index = temp + (0.5 * (humidity - 50))
                data["heat_index"] = round(heat_index, 2)

            # Classificar temperatura
            if temp is not None:
                if temp < 10:
                    data["temperature_category"] = "Frio"
                elif temp <= 25:
                    data["temperature_category"] = "Ameno"
                elif temp <= 35:
                    data["temperature_category"] = "Quente"
                else:
                    data["temperature_category"] = "Muito Quente"

            # Classificar umidade
            if humidity is not None:
                if humidity <= 30:
                    data["humidity_category"] = "Baixa"
                elif humidity < 60:
                    data["humidity_category"] = "Moderada"
                else:
                    data["humidity_category"] = "Alta"

            return data

        except Exception as e:
            logger.error(f"Erro ao adicionar campos derivados: {e}")
            return data


def main():
    """Função principal para teste do módulo"""
    # Dados de exemplo para teste
    sample_data = {
        "coord": {"lon": -46.6361, "lat": -23.5475},
        "weather": [
            {"id": 800, "main": "Clear", "description": "céu limpo", "icon": "01d"}
        ],
        "base": "stations",
        "main": {
            "temp": 25.5,
            "feels_like": 26.2,
            "temp_min": 23.1,
            "temp_max": 28.3,
            "pressure": 1013,
            "humidity": 65,
        },
        "visibility": 10000,
        "wind": {"speed": 3.5, "deg": 180},
        "clouds": {"all": 0},
        "dt": 1640995200,
        "sys": {
            "type": 1,
            "id": 8394,
            "country": "BR",
            "sunrise": 1640944800,
            "sunset": 1640995200,
        },
        "timezone": -10800,
        "id": 3448439,
        "name": "São Paulo",
        "cod": 200,
        "extracted_at": "2024-01-01T12:00:00",
    }

    # Criar transformador
    transformer = WeatherTransformer()

    # Testar transformação
    transformed = transformer.transform_weather_data(sample_data)

    if transformed:
        # Adicionar campos derivados
        final_data = transformer.add_derived_fields(transformed)

        print("Dados transformados com sucesso:")
        print(json.dumps(final_data, indent=2, ensure_ascii=False))
    else:
        print("Falha na transformação de dados")


if __name__ == "__main__":
    main()
