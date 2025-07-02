"""
Pipeline ETL principal para dados meteorológicos
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

import schedule

# Adicionar diretório atual ao path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from etl.extract import WeatherExtractor
from etl.load import WeatherLoader, get_db_config
from etl.transform import WeatherTransformer

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("/tmp/etl.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class WeatherETLPipeline:
    """Pipeline ETL completo para dados meteorológicos"""

    def __init__(self, api_key: str, db_config: Dict[str, str], cities: List[str]):
        """
        Inicializa o pipeline ETL

        Args:
            api_key (str): Chave da API OpenWeatherMap
            db_config (Dict[str, str]): Configurações do banco de dados
            cities (List[str]): Lista de cidades para monitorar
        """
        self.api_key = api_key
        self.db_config = db_config
        self.cities = cities

        # Inicializar componentes
        self.extractor = WeatherExtractor(api_key)
        self.transformer = WeatherTransformer()
        self.loader = WeatherLoader(db_config)

        # Estatísticas
        self.stats = {
            "total_runs": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "successful_loads": 0,
            "failed_loads": 0,
            "last_run": None,
            "last_success": None,
        }

    def setup_database(self) -> bool:
        """
        Configura o banco de dados

        Returns:
            bool: True se configurado com sucesso
        """
        try:
            if not self.loader.connect():
                logger.error("Falha ao conectar com o banco de dados")
                return False

            if not self.loader.create_tables():
                logger.error("Falha ao criar tabelas")
                return False

            logger.info("Banco de dados configurado com sucesso")
            return True

        except Exception as e:
            logger.error(f"Erro ao configurar banco de dados: {e}")
            return False

    def run_etl_for_city(self, city: str) -> bool:
        """
        Executa pipeline ETL para uma cidade específica

        Args:
            city (str): Nome da cidade

        Returns:
            bool: True se executado com sucesso
        """
        try:
            logger.info(f"Iniciando ETL para {city}")

            # 1. EXTRACT - Extrair dados da API
            raw_data = self.extractor.extract_weather_data(city)
            if not raw_data:
                logger.error(f"Falha na extração de dados para {city}")
                self.stats["failed_extractions"] += 1
                return False

            self.stats["successful_extractions"] += 1
            logger.info(f"Dados extraídos com sucesso para {city}")

            # 2. TRANSFORM - Transformar dados
            transformed_data = self.transformer.transform_weather_data(raw_data)
            if not transformed_data:
                logger.error(f"Falha na transformação de dados para {city}")
                return False

            # Adicionar campos derivados
            final_data = self.transformer.add_derived_fields(transformed_data)
            logger.info(f"Dados transformados com sucesso para {city}")

            # 3. LOAD - Carregar dados no banco
            if not self.loader.load_weather_data(final_data):
                logger.error(f"Falha no carregamento de dados para {city}")
                self.stats["failed_loads"] += 1
                return False

            self.stats["successful_loads"] += 1
            logger.info(f"Dados carregados com sucesso para {city}")

            return True

        except Exception as e:
            logger.error(f"Erro inesperado no ETL para {city}: {e}")
            return False

    def run_full_etl(self) -> Dict[str, Any]:
        """
        Executa pipeline ETL completo para todas as cidades

        Returns:
            Dict[str, Any]: Relatório de execução
        """
        start_time = datetime.now(timezone.utc)
        self.stats["total_runs"] += 1
        self.stats["last_run"] = start_time.isoformat()

        logger.info("=== INICIANDO PIPELINE ETL COMPLETO ===")

        # Garantir conexão com banco
        if not self.loader.connection:
            if not self.setup_database():
                return self._generate_report(start_time, success=False)

        results = {}
        successful_cities = 0

        # Executar ETL para cada cidade
        for city in self.cities:
            try:
                success = self.run_etl_for_city(city)
                results[city] = {
                    "success": success,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

                if success:
                    successful_cities += 1

                # Pequena pausa entre cidades para não sobrecarregar a API
                time.sleep(1)

            except Exception as e:
                logger.error(f"Erro crítico ao processar {city}: {e}")
                results[city] = {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

        # Atualizar estatísticas
        if successful_cities > 0:
            self.stats["last_success"] = datetime.now(timezone.utc).isoformat()

        # Gerar relatório
        report = self._generate_report(start_time, success=successful_cities > 0)
        report["city_results"] = results
        report["successful_cities"] = successful_cities
        report["total_cities"] = len(self.cities)

        logger.info(
            f"=== ETL CONCLUÍDO: {successful_cities}/{len(self.cities)} cidades processadas ==="
        )

        return report

    def _generate_report(self, start_time: datetime, success: bool) -> Dict[str, Any]:
        """
        Gera relatório de execução

        Args:
            start_time (datetime): Horário de início
            success (bool): Se a execução foi bem-sucedida

        Returns:
            Dict[str, Any]: Relatório
        """
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        return {
            "execution_id": f"etl_{int(start_time.timestamp())}",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "success": success,
            "statistics": self.stats.copy(),
        }

    def cleanup_old_data(self, days_to_keep: int = 30):
        """
        Remove dados antigos do banco

        Args:
            days_to_keep (int): Dias para manter os dados
        """
        try:
            if not self.loader.connection:
                self.setup_database()

            deleted_count = self.loader.cleanup_old_data(days_to_keep)
            logger.info(f"Limpeza concluída: {deleted_count} registros removidos")

        except Exception as e:
            logger.error(f"Erro na limpeza de dados: {e}")

    def get_health_status(self) -> Dict[str, Any]:
        """
        Retorna status de saúde do pipeline

        Returns:
            Dict[str, Any]: Status de saúde
        """
        try:
            # Verificar conexão com banco
            db_healthy = self.loader.connection is not None

            # Verificar última execução
            last_run_ok = False
            if self.stats["last_run"]:
                last_run = datetime.fromisoformat(self.stats["last_run"])
                hours_since_last_run = (
                    datetime.now(timezone.utc) - last_run
                ).total_seconds() / 3600
                last_run_ok = hours_since_last_run < 2  # Menos de 2 horas

            # Status geral
            overall_healthy = db_healthy and last_run_ok

            return {
                "healthy": overall_healthy,
                "database_connected": db_healthy,
                "last_run_recent": last_run_ok,
                "statistics": self.stats,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Erro ao verificar status de saúde: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }


def get_config() -> Dict[str, Any]:
    """
    Recupera configurações das variáveis de ambiente

    Returns:
        Dict[str, Any]: Configurações
    """
    return {
        "api_key": os.getenv("OPENWEATHER_API_KEY", "your_api_key_here"),
        "cities": os.getenv("CITIES", "São Paulo,Rio de Janeiro,Belo Horizonte").split(
            ","
        ),
        "schedule_interval": int(os.getenv("SCHEDULE_INTERVAL_MINUTES", "60")),
        "cleanup_days": int(os.getenv("CLEANUP_DAYS", "30")),
    }


def run_scheduled_etl():
    """Função para execução agendada do ETL"""
    try:
        config = get_config()
        db_config = get_db_config()

        # Criar pipeline
        pipeline = WeatherETLPipeline(
            api_key=config["api_key"],
            db_config=db_config,
            cities=[city.strip() for city in config["cities"]],
        )

        # Executar ETL
        report = pipeline.run_full_etl()

        # Log do relatório
        logger.info(
            f"Relatório de execução: {json.dumps(report, indent=2, default=str)}"
        )

        # Limpeza semanal (apenas aos domingos)
        if datetime.now().weekday() == 6:  # Domingo
            pipeline.cleanup_old_data(config["cleanup_days"])

    except Exception as e:
        logger.error(f"Erro na execução agendada: {e}")


def main():
    """Função principal"""
    config = get_config()

    if config["api_key"] == "your_api_key_here":
        logger.warning(
            "Usando chave de API padrão. Configure OPENWEATHER_API_KEY para usar uma chave real."
        )

    # Verificar modo de execução
    mode = os.getenv("ETL_MODE", "once")

    if mode == "schedule":
        # Modo agendado
        logger.info(
            f"Iniciando modo agendado - execução a cada {config['schedule_interval']} minutos"
        )

        # Agendar execução
        schedule.every(config["schedule_interval"]).minutes.do(run_scheduled_etl)

        # Executar uma vez imediatamente
        run_scheduled_etl()

        # Loop principal
        while True:
            schedule.run_pending()
            time.sleep(60)  # Verificar a cada minuto

    else:
        # Modo execução única
        logger.info("Executando ETL uma única vez")
        run_scheduled_etl()


if __name__ == "__main__":
    main()
