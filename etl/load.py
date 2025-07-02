"""
Módulo de carregamento de dados no PostgreSQL
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WeatherLoader:
    """Classe responsável pelo carregamento de dados no PostgreSQL"""

    def __init__(self, db_config: Dict[str, str]):
        """
        Inicializa o carregador com configurações do banco

        Args:
            db_config (Dict[str, str]): Configurações de conexão do banco
        """
        self.db_config = db_config
        self.connection = None

    def connect(self) -> bool:
        """
        Estabelece conexão com o banco de dados

        Returns:
            bool: True se conectado com sucesso, False caso contrário
        """
        try:
            self.connection = psycopg2.connect(
                host=self.db_config["host"],
                port=self.db_config["port"],
                database=self.db_config["database"],
                user=self.db_config["user"],
                password=self.db_config["password"],
            )
            self.connection.autocommit = True
            logger.info("Conexão com PostgreSQL estabelecida com sucesso")
            return True

        except psycopg2.Error as e:
            logger.error(f"Erro ao conectar com PostgreSQL: {e}")
            return False

    def disconnect(self):
        """Fecha conexão com o banco de dados"""
        if self.connection:
            self.connection.close()
            logger.info("Conexão com PostgreSQL fechada")

    def create_tables(self) -> bool:
        """
        Cria tabelas necessárias no banco de dados

        Returns:
            bool: True se criadas com sucesso, False caso contrário
        """
        try:
            cursor = self.connection.cursor()

            # SQL para criar tabela de dados meteorológicos
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS weather_data (
                id SERIAL PRIMARY KEY,
                city_id INTEGER,
                city_name VARCHAR(100) NOT NULL,
                country_code VARCHAR(10),
                latitude DECIMAL(10, 8),
                longitude DECIMAL(11, 8),
                temperature DECIMAL(5, 2),
                temperature_feels_like DECIMAL(5, 2),
                temperature_min DECIMAL(5, 2),
                temperature_max DECIMAL(5, 2),
                pressure INTEGER,
                humidity INTEGER,
                sea_level_pressure INTEGER,
                ground_level_pressure INTEGER,
                weather_main VARCHAR(50),
                weather_description VARCHAR(200),
                weather_icon VARCHAR(10),
                wind_speed DECIMAL(5, 2),
                wind_direction INTEGER,
                wind_gust DECIMAL(5, 2),
                cloudiness INTEGER,
                visibility INTEGER,
                data_timestamp TIMESTAMP,
                sunrise TIMESTAMP,
                sunset TIMESTAMP,
                extracted_at TIMESTAMP,
                processed_at TIMESTAMP,
                timezone_offset INTEGER,
                heat_index DECIMAL(5, 2),
                temperature_category VARCHAR(20),
                humidity_category VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_weather_city_name ON weather_data(city_name);
            CREATE INDEX IF NOT EXISTS idx_weather_data_timestamp ON weather_data(data_timestamp);
            CREATE INDEX IF NOT EXISTS idx_weather_created_at ON weather_data(created_at);
            """

            cursor.execute(create_table_sql)
            logger.info("Tabelas criadas com sucesso")
            return True

        except psycopg2.Error as e:
            logger.error(f"Erro ao criar tabelas: {e}")
            return False
        finally:
            if cursor:
                cursor.close()

    def load_weather_data(self, data: Dict[str, Any]) -> bool:
        """
        Carrega dados meteorológicos na tabela

        Args:
            data (Dict[str, Any]): Dados transformados para carregar

        Returns:
            bool: True se carregado com sucesso, False caso contrário
        """
        try:
            cursor = self.connection.cursor()

            # SQL de inserção
            insert_sql = """
            INSERT INTO weather_data (
                city_id, city_name, country_code, latitude, longitude,
                temperature, temperature_feels_like, temperature_min, temperature_max,
                pressure, humidity, sea_level_pressure, ground_level_pressure,
                weather_main, weather_description, weather_icon,
                wind_speed, wind_direction, wind_gust,
                cloudiness, visibility,
                data_timestamp, sunrise, sunset, extracted_at, processed_at,
                timezone_offset, heat_index, temperature_category, humidity_category
            ) VALUES (
                %(city_id)s, %(city_name)s, %(country_code)s, %(latitude)s, %(longitude)s,
                %(temperature)s, %(temperature_feels_like)s, %(temperature_min)s, %(temperature_max)s,
                %(pressure)s, %(humidity)s, %(sea_level_pressure)s, %(ground_level_pressure)s,
                %(weather_main)s, %(weather_description)s, %(weather_icon)s,
                %(wind_speed)s, %(wind_direction)s, %(wind_gust)s,
                %(cloudiness)s, %(visibility)s,
                %(data_timestamp)s, %(sunrise)s, %(sunset)s, %(extracted_at)s, %(processed_at)s,
                %(timezone_offset)s, %(heat_index)s, %(temperature_category)s, %(humidity_category)s
            )
            """

            # Preparar dados para inserção
            insert_data = self._prepare_data_for_insert(data)

            cursor.execute(insert_sql, insert_data)
            logger.info(f"Dados carregados com sucesso para {data.get('city_name')}")
            return True

        except psycopg2.Error as e:
            logger.error(f"Erro ao carregar dados: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro inesperado ao carregar dados: {e}")
            return False
        finally:
            if cursor:
                cursor.close()

    def _prepare_data_for_insert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepara dados para inserção no banco

        Args:
            data (Dict[str, Any]): Dados originais

        Returns:
            Dict[str, Any]: Dados preparados
        """

        # Converter timestamps string para datetime
        def parse_timestamp(ts_str):
            if ts_str:
                try:
                    return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                except:
                    return None
            return None

        prepared_data = data.copy()

        # Converter timestamps
        timestamp_fields = [
            "data_timestamp",
            "sunrise",
            "sunset",
            "extracted_at",
            "processed_at",
        ]
        for field in timestamp_fields:
            if field in prepared_data:
                prepared_data[field] = parse_timestamp(prepared_data[field])

        return prepared_data

    def load_multiple_records(self, data_list: List[Dict[str, Any]]) -> int:
        """
        Carrega múltiplos registros de uma vez

        Args:
            data_list (List[Dict[str, Any]]): Lista de dados para carregar

        Returns:
            int: Número de registros carregados com sucesso
        """
        success_count = 0

        for data in data_list:
            if self.load_weather_data(data):
                success_count += 1

        logger.info(f"Carregados {success_count} de {len(data_list)} registros")
        return success_count

    def get_latest_data(
        self, city_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Recupera os dados mais recentes

        Args:
            city_name (Optional[str]): Nome da cidade (opcional)

        Returns:
            Optional[Dict[str, Any]]: Dados mais recentes ou None
        """
        try:
            cursor = self.connection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            )

            if city_name:
                sql = """
                SELECT * FROM weather_data 
                WHERE city_name = %s 
                ORDER BY data_timestamp DESC 
                LIMIT 1
                """
                cursor.execute(sql, (city_name,))
            else:
                sql = """
                SELECT * FROM weather_data 
                ORDER BY data_timestamp DESC 
                LIMIT 1
                """
                cursor.execute(sql)

            result = cursor.fetchone()
            return dict(result) if result else None

        except psycopg2.Error as e:
            logger.error(f"Erro ao recuperar dados: {e}")
            return None
        finally:
            if cursor:
                cursor.close()

    def get_data_by_city(self, city_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Recupera dados por cidade

        Args:
            city_name (str): Nome da cidade
            limit (int): Limite de registros

        Returns:
            List[Dict[str, Any]]: Lista de dados
        """
        try:
            cursor = self.connection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            )

            sql = """
            SELECT * FROM weather_data 
            WHERE city_name ILIKE %s 
            ORDER BY data_timestamp DESC 
            LIMIT %s
            """

            cursor.execute(sql, (f"%{city_name}%", limit))
            results = cursor.fetchall()

            return [dict(row) for row in results]

        except psycopg2.Error as e:
            logger.error(f"Erro ao recuperar dados por cidade: {e}")
            return []
        finally:
            if cursor:
                cursor.close()

    def cleanup_old_data(self, days_to_keep: int = 30) -> int:
        """
        Remove dados antigos do banco

        Args:
            days_to_keep (int): Número de dias para manter

        Returns:
            int: Número de registros removidos
        """
        try:
            cursor = self.connection.cursor()

            sql = """
            DELETE FROM weather_data 
            WHERE created_at < NOW() - INTERVAL '%s days'
            """

            cursor.execute(sql, (days_to_keep,))
            deleted_count = cursor.rowcount

            logger.info(f"Removidos {deleted_count} registros antigos")
            return deleted_count

        except psycopg2.Error as e:
            logger.error(f"Erro ao limpar dados antigos: {e}")
            return 0
        finally:
            if cursor:
                cursor.close()


def get_db_config() -> Dict[str, str]:
    """
    Recupera configurações do banco de dados das variáveis de ambiente

    Returns:
        Dict[str, str]: Configurações do banco
    """
    return {
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT", "5432"),
        "database": os.getenv("DB_NAME", "weather_db"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", "postgres"),
    }


def main():
    """Função principal para teste do módulo"""
    # Configurações do banco
    db_config = get_db_config()

    # Criar loader
    loader = WeatherLoader(db_config)

    # Conectar
    if not loader.connect():
        print("Falha na conexão com o banco")
        return

    # Criar tabelas
    if not loader.create_tables():
        print("Falha ao criar tabelas")
        return

    # Dados de exemplo para teste
    sample_data = {
        "city_id": 3448439,
        "city_name": "São Paulo",
        "country_code": "BR",
        "latitude": -23.5475,
        "longitude": -46.6361,
        "temperature": 25.5,
        "temperature_feels_like": 26.2,
        "temperature_min": 23.1,
        "temperature_max": 28.3,
        "pressure": 1013,
        "humidity": 65,
        "weather_main": "Clear",
        "weather_description": "céu limpo",
        "weather_icon": "01d",
        "wind_speed": 3.5,
        "wind_direction": 180,
        "cloudiness": 0,
        "visibility": 10000,
        "data_timestamp": "2024-01-01T12:00:00",
        "extracted_at": "2024-01-01T12:00:00",
        "processed_at": "2024-01-01T12:01:00",
        "timezone_offset": -10800,
        "heat_index": 27.5,
        "temperature_category": "Quente",
        "humidity_category": "Moderada",
    }

    # Testar carregamento
    if loader.load_weather_data(sample_data):
        print("Dados carregados com sucesso")

        # Testar recuperação
        latest = loader.get_latest_data()
        if latest:
            print("Dados mais recentes:")
            print(json.dumps(dict(latest), indent=2, ensure_ascii=False, default=str))
    else:
        print("Falha no carregamento de dados")

    # Desconectar
    loader.disconnect()


if __name__ == "__main__":
    main()
