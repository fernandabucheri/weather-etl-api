# Makefile para Weather ETL API
# Facilita a execução de comandos comuns do projeto

.PHONY: help install test lint format clean build up down logs shell-api shell-etl shell-db

# Variáveis
PYTHON := python3
PIP := pip3
DOCKER_COMPOSE := docker-compose

# Comando padrão
help: ## Mostra esta mensagem de ajuda
	@echo "Weather ETL API - Comandos disponíveis:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Instalação e configuração
install: ## Instala dependências do projeto
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install-dev: ## Instala dependências de desenvolvimento
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install pre-commit
	pre-commit install

# Qualidade de código
lint: ## Executa verificação de código (flake8)
	flake8 .

format: ## Formata código (black + isort)
	black .
	isort .

format-check: ## Verifica formatação sem modificar arquivos
	black --check --diff .
	isort --check-only --diff .

# Testes
test: ## Executa todos os testes
	pytest

test-cov: ## Executa testes com cobertura
	pytest --cov=etl --cov=api --cov-report=html --cov-report=term-missing

test-unit: ## Executa apenas testes unitários
	pytest -m unit

test-integration: ## Executa apenas testes de integração
	pytest -m integration

test-api: ## Executa apenas testes da API
	pytest -m api

test-etl: ## Executa apenas testes do ETL
	pytest -m etl

# Docker
build: ## Constrói imagens Docker
	$(DOCKER_COMPOSE) build

up: ## Inicia todos os serviços
	$(DOCKER_COMPOSE) up -d

up-logs: ## Inicia serviços e mostra logs
	$(DOCKER_COMPOSE) up

down: ## Para todos os serviços
	$(DOCKER_COMPOSE) down

down-volumes: ## Para serviços e remove volumes
	$(DOCKER_COMPOSE) down -v

restart: ## Reinicia todos os serviços
	$(DOCKER_COMPOSE) restart

logs: ## Mostra logs de todos os serviços
	$(DOCKER_COMPOSE) logs -f

logs-api: ## Mostra logs da API
	$(DOCKER_COMPOSE) logs -f api

logs-etl: ## Mostra logs do ETL
	$(DOCKER_COMPOSE) logs -f etl

logs-db: ## Mostra logs do banco
	$(DOCKER_COMPOSE) logs -f postgres

# Shells interativos
shell-api: ## Acessa shell do container da API
	$(DOCKER_COMPOSE) exec api /bin/bash

shell-etl: ## Acessa shell do container do ETL
	$(DOCKER_COMPOSE) exec etl /bin/bash

shell-db: ## Acessa shell do PostgreSQL
	$(DOCKER_COMPOSE) exec postgres psql -U postgres -d weather_db

# Desenvolvimento local
dev-setup: ## Configuração inicial para desenvolvimento
	@echo "🚀 Configurando ambiente de desenvolvimento..."
	@if [ ! -f .env ]; then \
		echo "📝 Criando arquivo .env..."; \
		cp .env.example .env; \
		echo "⚠️  Configure sua chave da API no arquivo .env"; \
	fi
	make install-dev
	@echo "✅ Ambiente configurado! Execute 'make up' para iniciar os serviços."

dev-api: ## Executa API em modo desenvolvimento
	cd api && uvicorn main:app --reload --host 0.0.0.0 --port 8000

dev-etl: ## Executa ETL uma vez em modo desenvolvimento
	cd etl && $(PYTHON) main_etl.py

# Limpeza
clean: ## Remove arquivos temporários
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf dist/
	rm -rf build/

clean-docker: ## Remove imagens e volumes Docker
	$(DOCKER_COMPOSE) down -v --rmi all
	docker system prune -f

# Banco de dados
db-reset: ## Reseta banco de dados (CUIDADO: apaga todos os dados)
	$(DOCKER_COMPOSE) down -v
	$(DOCKER_COMPOSE) up -d postgres
	@echo "⚠️  Banco de dados resetado!"

db-backup: ## Faz backup do banco de dados
	@echo "💾 Fazendo backup do banco..."
	$(DOCKER_COMPOSE) exec postgres pg_dump -U postgres weather_db > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup salvo!"

# Monitoramento
status: ## Mostra status dos serviços
	$(DOCKER_COMPOSE) ps

health: ## Verifica saúde da API
	@echo "🏥 Verificando saúde da API..."
	@curl -s http://localhost:8000/health | python -m json.tool || echo "❌ API não está respondendo"

stats: ## Mostra estatísticas dos dados
	@echo "📊 Estatísticas dos dados meteorológicos..."
	@curl -s http://localhost:8000/weather/stats | python -m json.tool || echo "❌ API não está respondendo"

# CI/CD local
ci-local: ## Executa pipeline CI/CD localmente
	@echo "🔄 Executando pipeline CI/CD local..."
	make format-check
	make lint
	make test-cov
	make build
	@echo "✅ Pipeline local concluído com sucesso!"

# Documentação
docs: ## Abre documentação da API
	@echo "📚 Abrindo documentação da API..."
	@echo "Swagger UI: http://localhost:8000/docs"
	@echo "ReDoc: http://localhost:8000/redoc"

# Utilitários
env-check: ## Verifica variáveis de ambiente
	@echo "🔍 Verificando configuração do ambiente..."
	@echo "Arquivo .env existe: $(shell [ -f .env ] && echo '✅ Sim' || echo '❌ Não')"
	@echo "Docker está rodando: $(shell docker info >/dev/null 2>&1 && echo '✅ Sim' || echo '❌ Não')"
	@echo "Docker Compose disponível: $(shell command -v docker-compose >/dev/null 2>&1 && echo '✅ Sim' || echo '❌ Não')"

ports: ## Mostra portas utilizadas pelo projeto
	@echo "🔌 Portas utilizadas:"
	@echo "  - API: http://localhost:8000"
	@echo "  - Adminer: http://localhost:8080"
	@echo "  - PostgreSQL: localhost:5432"

# Exemplo de uso
example: ## Mostra exemplos de uso da API
	@echo "🌟 Exemplos de uso da API:"
	@echo ""
	@echo "1. Dados mais recentes:"
	@echo "   curl http://localhost:8000/weather/latest"
	@echo ""
	@echo "2. Dados por cidade:"
	@echo "   curl 'http://localhost:8000/weather/by_city?city=São Paulo'"
	@echo ""
	@echo "3. Cidades disponíveis:"
	@echo "   curl http://localhost:8000/weather/cities"
	@echo ""
	@echo "4. Estatísticas:"
	@echo "   curl http://localhost:8000/weather/stats"

