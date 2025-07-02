"""
API FastAPI para dados meteorológicos
"""

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Adicionar diretório ETL ao path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "etl"))

from etl.load import WeatherLoader, get_db_config

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Criar aplicação FastAPI
app = FastAPI(
    title="Weather ETL API",
    description="API para consulta de dados meteorológicos coletados via ETL",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Modelos Pydantic
class WeatherResponse(BaseModel):
    """Modelo de resposta para dados meteorológicos"""

    id: Optional[int] = Field(None, description="ID do registro")
    city_id: Optional[int] = Field(None, description="ID da cidade")
    city_name: str = Field(..., description="Nome da cidade")
    country_code: Optional[str] = Field(None, description="Código do país")
    latitude: Optional[float] = Field(None, description="Latitude")
    longitude: Optional[float] = Field(None, description="Longitude")
    temperature: Optional[float] = Field(None, description="Temperatura em Celsius")
    temperature_feels_like: Optional[float] = Field(
        None, description="Sensação térmica"
    )
    temperature_min: Optional[float] = Field(None, description="Temperatura mínima")
    temperature_max: Optional[float] = Field(None, description="Temperatura máxima")
    pressure: Optional[int] = Field(None, description="Pressão atmosférica")
    humidity: Optional[int] = Field(None, description="Umidade relativa")
    weather_main: Optional[str] = Field(
        None, description="Condição meteorológica principal"
    )
    weather_description: Optional[str] = Field(None, description="Descrição detalhada")
    wind_speed: Optional[float] = Field(None, description="Velocidade do vento")
    wind_direction: Optional[int] = Field(None, description="Direção do vento")
    cloudiness: Optional[int] = Field(None, description="Nebulosidade")
    visibility: Optional[int] = Field(None, description="Visibilidade")
    data_timestamp: Optional[str] = Field(None, description="Timestamp dos dados")
    heat_index: Optional[float] = Field(None, description="Índice de calor")
    temperature_category: Optional[str] = Field(
        None, description="Categoria de temperatura"
    )
    humidity_category: Optional[str] = Field(None, description="Categoria de umidade")
    created_at: Optional[str] = Field(None, description="Timestamp de criação")


class HealthResponse(BaseModel):
    """Modelo de resposta para status de saúde"""

    status: str = Field(..., description="Status da API")
    timestamp: str = Field(..., description="Timestamp da verificação")
    database_connected: bool = Field(..., description="Status da conexão com banco")
    version: str = Field(..., description="Versão da API")


class ErrorResponse(BaseModel):
    """Modelo de resposta para erros"""

    error: str = Field(..., description="Mensagem de erro")
    detail: Optional[str] = Field(None, description="Detalhes do erro")
    timestamp: str = Field(..., description="Timestamp do erro")


# Dependência para conexão com banco
def get_weather_loader():
    """Dependência para obter loader de dados meteorológicos"""
    try:
        db_config = get_db_config()
        loader = WeatherLoader(db_config)

        if not loader.connect():
            raise HTTPException(
                status_code=503, detail="Não foi possível conectar com o banco de dados"
            )

        return loader
    except Exception as e:
        logger.error(f"Erro ao criar loader: {e}")
        raise HTTPException(status_code=503, detail="Erro interno do servidor")


# Endpoints
@app.get("/", response_model=Dict[str, str])
async def root():
    """Endpoint raiz da API"""
    return {
        "message": "Weather ETL API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse)
async def health_check(loader: WeatherLoader = Depends(get_weather_loader)):
    """Endpoint para verificação de saúde da API"""
    try:
        # Testar conexão com banco
        db_connected = loader.connection is not None

        return HealthResponse(
            status="healthy" if db_connected else "unhealthy",
            timestamp=datetime.now(timezone.utc).isoformat(),
            database_connected=db_connected,
            version="1.0.0",
        )
    except Exception as e:
        logger.error(f"Erro no health check: {e}")
        raise HTTPException(status_code=503, detail="Erro na verificação de saúde")
    finally:
        if loader:
            loader.disconnect()


@app.get("/weather/latest", response_model=WeatherResponse)
async def get_latest_weather(
    city: Optional[str] = Query(None, description="Nome da cidade (opcional)"),
    loader: WeatherLoader = Depends(get_weather_loader),
):
    """
    Retorna os dados meteorológicos mais recentes

    Args:
        city: Nome da cidade (opcional). Se não fornecido, retorna o mais recente geral.

    Returns:
        WeatherResponse: Dados meteorológicos mais recentes
    """
    try:
        # Buscar dados mais recentes
        data = loader.get_latest_data(city_name=city)

        if not data:
            city_msg = f" para {city}" if city else ""
            raise HTTPException(
                status_code=404,
                detail=f"Nenhum dado meteorológico encontrado{city_msg}",
            )

        # Converter timestamps para string
        for field in [
            "data_timestamp",
            "sunrise",
            "sunset",
            "extracted_at",
            "processed_at",
            "created_at",
        ]:
            if field in data and data[field]:
                data[field] = (
                    data[field].isoformat()
                    if hasattr(data[field], "isoformat")
                    else str(data[field])
                )

        return WeatherResponse(**data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar dados mais recentes: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")
    finally:
        if loader:
            loader.disconnect()


@app.get("/weather/by_city", response_model=List[WeatherResponse])
async def get_weather_by_city(
    city: str = Query(..., description="Nome da cidade"),
    limit: int = Query(10, ge=1, le=100, description="Número máximo de registros"),
    loader: WeatherLoader = Depends(get_weather_loader),
):
    """
    Retorna dados meteorológicos filtrados por cidade

    Args:
        city: Nome da cidade
        limit: Número máximo de registros (1-100)

    Returns:
        List[WeatherResponse]: Lista de dados meteorológicos
    """
    try:
        # Buscar dados por cidade
        data_list = loader.get_data_by_city(city_name=city, limit=limit)

        if not data_list:
            raise HTTPException(
                status_code=404,
                detail=f"Nenhum dado meteorológico encontrado para {city}",
            )

        # Converter timestamps para string
        for data in data_list:
            for field in [
                "data_timestamp",
                "sunrise",
                "sunset",
                "extracted_at",
                "processed_at",
                "created_at",
            ]:
                if field in data and data[field]:
                    data[field] = (
                        data[field].isoformat()
                        if hasattr(data[field], "isoformat")
                        else str(data[field])
                    )

        return [WeatherResponse(**data) for data in data_list]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar dados por cidade: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")
    finally:
        if loader:
            loader.disconnect()


@app.get("/weather/cities", response_model=List[str])
async def get_available_cities(loader: WeatherLoader = Depends(get_weather_loader)):
    """
    Retorna lista de cidades disponíveis no banco de dados

    Returns:
        List[str]: Lista de nomes de cidades
    """
    try:
        cursor = loader.connection.cursor()

        sql = """
        SELECT DISTINCT city_name 
        FROM weather_data 
        ORDER BY city_name
        """

        cursor.execute(sql)
        results = cursor.fetchall()

        cities = [row[0] for row in results]

        return cities

    except Exception as e:
        logger.error(f"Erro ao buscar cidades disponíveis: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")
    finally:
        if cursor:
            cursor.close()
        if loader:
            loader.disconnect()


@app.get("/weather/stats", response_model=Dict[str, Any])
async def get_weather_stats(loader: WeatherLoader = Depends(get_weather_loader)):
    """
    Retorna estatísticas dos dados meteorológicos

    Returns:
        Dict[str, Any]: Estatísticas dos dados
    """
    try:
        cursor = loader.connection.cursor()

        # Estatísticas gerais
        stats_sql = """
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT city_name) as total_cities,
            MIN(data_timestamp) as oldest_data,
            MAX(data_timestamp) as newest_data,
            AVG(temperature) as avg_temperature,
            MIN(temperature) as min_temperature,
            MAX(temperature) as max_temperature,
            AVG(humidity) as avg_humidity
        FROM weather_data
        """

        cursor.execute(stats_sql)
        stats = cursor.fetchone()

        # Dados por cidade
        city_stats_sql = """
        SELECT 
            city_name,
            COUNT(*) as record_count,
            AVG(temperature) as avg_temp,
            MAX(data_timestamp) as last_update
        FROM weather_data 
        GROUP BY city_name 
        ORDER BY record_count DESC
        """

        cursor.execute(city_stats_sql)
        city_stats = cursor.fetchall()

        return {
            "total_records": stats[0],
            "total_cities": stats[1],
            "oldest_data": stats[2].isoformat() if stats[2] else None,
            "newest_data": stats[3].isoformat() if stats[3] else None,
            "average_temperature": round(float(stats[4]), 2) if stats[4] else None,
            "min_temperature": float(stats[5]) if stats[5] else None,
            "max_temperature": float(stats[6]) if stats[6] else None,
            "average_humidity": round(float(stats[7]), 2) if stats[7] else None,
            "cities": [
                {
                    "name": row[0],
                    "record_count": row[1],
                    "avg_temperature": round(float(row[2]), 2) if row[2] else None,
                    "last_update": row[3].isoformat() if row[3] else None,
                }
                for row in city_stats
            ],
        }

    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")
    finally:
        if cursor:
            cursor.close()
        if loader:
            loader.disconnect()


# Handler de exceções global
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handler global para exceções não tratadas"""
    logger.error(f"Erro não tratado: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Erro interno do servidor",
            detail=str(exc),
            timestamp=datetime.now(timezone.utc).isoformat(),
        ).dict(),
    )


# Configuração para execução
def create_app():
    """Factory function para criar a aplicação"""
    return app


if __name__ == "__main__":
    # Configurações do servidor
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"

    logger.info(f"Iniciando API em {host}:{port}")

    uvicorn.run("main:app", host=host, port=port, reload=debug, log_level="info")
