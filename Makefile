.PHONY: setup test lint format compose-up compose-down ingest transform dbt-run dashboard quality health clean

setup:
	python -m pip install -e ".[dev]"

test:
	python -m pytest

lint:
	ruff check .
	ruff format --check .

format:
	ruff check --fix .
	ruff format .

compose-up:
	docker compose up -d --build

compose-down:
	docker compose down

ingest:
	python scripts/ingest_ibge_municipalities.py
	python scripts/ingest_ibge_population.py
	python scripts/ingest_anatel_broadband_2026.py

transform:
	python scripts/build_ibge_municipality_bronze.py
	python scripts/build_ibge_municipality_silver.py
	python scripts/build_ibge_population_layers.py
	python scripts/build_dimensions.py
	python scripts/build_anatel_broadband_bronze.py
	python scripts/build_anatel_broadband_silver.py
	python scripts/build_fact_broadband_accesses.py
	python scripts/build_broadband_marts.py

dbt-run:
	python scripts/load_gold_to_postgres.py
	cd dbt && dbt build --profiles-dir .

dashboard:
	streamlit run streamlit/app.py

health:
	python scripts/check_platform_health.py

quality:
	python scripts/profile_ibge_municipalities.py
	python scripts/profile_ibge_population.py
	python scripts/profile_anatel_broadband.py
	python -m pytest tests/data_quality

clean:
	python scripts/clean_generated.py
