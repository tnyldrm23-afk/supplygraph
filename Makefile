PYTHON ?= python3.12
VENV := .venv/bin
INTEGRATION ?= 0
.DEFAULT_GOAL := help
.PHONY: help setup venv install run docker-build docker-run docker-stop model test test-integration lint format clean data seed benchmark ml demo verify
help: ## Show project commands
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
setup: ## Generate a private local .env with random database password
	$(PYTHON) scripts/setup.py
venv: ## Create isolated Python environment (Python 3.12)
	@test -d .venv || $(PYTHON) -m venv .venv
install: venv ## Install pinned development dependencies
	$(VENV)/pip install -r requirements-lock.txt
run: setup ## Run API locally (requires Neo4j; UI through Docker on :8080)
	$(VENV)/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
docker-build: setup ## Build the API container
	docker compose build
docker-run: setup ## Start all four services and wait for readiness
	docker compose up --build -d --wait --wait-timeout 300
docker-stop: ## Stop project containers, preserving data and model volumes
	docker compose down
model: ## Pull the configured local LLM (about 1 GB, first run only)
	$(VENV)/python scripts/pull_model.py
test: ## Run unit/API/security tests and produce coverage report
	$(VENV)/pytest -q -m 'not integration' --cov=app --cov-report=term-missing --cov-report=xml:reports/coverage.xml
	@if [ "$(INTEGRATION)" = "1" ]; then $(MAKE) test-integration; fi
test-integration: ## Test real Neo4j, Cypher, GDS and container-facing API
	$(VENV)/pytest -q -m integration
lint: ## Require pylint >=9.5 for application code
	$(VENV)/pylint app --fail-under=9.5
format: ## Format Python code
	$(VENV)/black app scripts tests
clean: ## Remove Python/test caches; preserve data, credentials and containers
	$(PYTHON) scripts/clean.py
data: ## Download, verify and sanitize original DataCo dataset
	$(VENV)/python scripts/download_data.py
	$(VENV)/python scripts/prepare_data.py
seed: ## Idempotently re-import the committed sanitized dataset
	$(VENV)/python -m scripts.seed_data
benchmark: ## Record real Cypher PROFILE plans and latency measurements
	$(VENV)/python -m scripts.benchmark
ml: ## Train and evaluate a chronological order-classification baseline
	$(VENV)/python -m scripts.train_model
demo: ## Execute demonstration notebook against the running stack
	$(VENV)/python scripts/run_notebook.py
verify: lint test test-integration ## Run application release quality gates
