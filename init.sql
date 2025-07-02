-- Script de inicialização do banco de dados PostgreSQL
-- Este script é executado automaticamente quando o container PostgreSQL é criado

-- Criar extensões úteis
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Configurar timezone
SET timezone = 'UTC';

-- Criar tabela de dados meteorológicos
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

-- Criar índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_weather_city_name ON weather_data(city_name);
CREATE INDEX IF NOT EXISTS idx_weather_data_timestamp ON weather_data(data_timestamp);
CREATE INDEX IF NOT EXISTS idx_weather_created_at ON weather_data(created_at);
CREATE INDEX IF NOT EXISTS idx_weather_country_code ON weather_data(country_code);

-- Criar tabela de logs de ETL (opcional)
CREATE TABLE IF NOT EXISTS etl_logs (
    id SERIAL PRIMARY KEY,
    execution_id VARCHAR(100) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status VARCHAR(20) NOT NULL, -- 'running', 'success', 'failed'
    cities_processed INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_etl_logs_execution_id ON etl_logs(execution_id);
CREATE INDEX IF NOT EXISTS idx_etl_logs_start_time ON etl_logs(start_time);
CREATE INDEX IF NOT EXISTS idx_etl_logs_status ON etl_logs(status);

-- Inserir dados de exemplo (opcional)
INSERT INTO weather_data (
    city_name, country_code, latitude, longitude,
    temperature, humidity, pressure, weather_main, weather_description,
    data_timestamp, extracted_at, processed_at,
    temperature_category, humidity_category
) VALUES 
(
    'São Paulo', 'BR', -23.5475, -46.6361,
    25.0, 65, 1013, 'Clear', 'céu limpo',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
    'Ameno', 'Moderada'
),
(
    'Rio de Janeiro', 'BR', -22.9068, -43.1729,
    28.0, 70, 1015, 'Clouds', 'nuvens dispersas',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
    'Quente', 'Alta'
)
ON CONFLICT DO NOTHING;

-- Criar função para limpeza automática de dados antigos
CREATE OR REPLACE FUNCTION cleanup_old_weather_data(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM weather_data 
    WHERE created_at < NOW() - INTERVAL '1 day' * days_to_keep;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    INSERT INTO etl_logs (execution_id, start_time, end_time, status, records_inserted)
    VALUES (
        'cleanup_' || EXTRACT(EPOCH FROM NOW()),
        NOW(),
        NOW(),
        'success',
        -deleted_count
    );
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Criar view para estatísticas rápidas
CREATE OR REPLACE VIEW weather_stats AS
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT city_name) as total_cities,
    MIN(data_timestamp) as oldest_data,
    MAX(data_timestamp) as newest_data,
    ROUND(AVG(temperature), 2) as avg_temperature,
    MIN(temperature) as min_temperature,
    MAX(temperature) as max_temperature,
    ROUND(AVG(humidity), 2) as avg_humidity,
    COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '24 hours') as records_last_24h
FROM weather_data;

-- Criar view para dados por cidade
CREATE OR REPLACE VIEW weather_by_city AS
SELECT 
    city_name,
    country_code,
    COUNT(*) as record_count,
    ROUND(AVG(temperature), 2) as avg_temperature,
    ROUND(AVG(humidity), 2) as avg_humidity,
    MAX(data_timestamp) as last_update,
    MAX(created_at) as last_insert
FROM weather_data 
GROUP BY city_name, country_code
ORDER BY record_count DESC;

-- Configurações de performance
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_duration = on;

-- Mensagem de sucesso
DO $$
BEGIN
    RAISE NOTICE 'Banco de dados inicializado com sucesso!';
    RAISE NOTICE 'Tabelas criadas: weather_data, etl_logs';
    RAISE NOTICE 'Views criadas: weather_stats, weather_by_city';
    RAISE NOTICE 'Função criada: cleanup_old_weather_data()';
END $$;

