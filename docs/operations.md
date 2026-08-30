# Operação local

## Dependências

- Python 3.11 ou 3.12;
- PostgreSQL 16;
- dependências `.[dev,analytics,dashboard]`;
- Docker é opcional para a execução local nativa.

## Banco e dbt

Defina `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER` e
`POSTGRES_PASSWORD`. Depois execute, na raiz:

```bash
python scripts/load_gold_to_postgres.py
cd dbt
dbt build --profiles-dir .
```

A carga substitui somente as três tabelas fonte do schema `gold`. Os marts são materializados no
schema `analytics`. Senhas permanecem em variáveis de ambiente e `dbt/profiles.yml` é ignorado
pelo Git.

## Dashboard

```bash
streamlit run streamlit/app.py
```

O dashboard usa os marts Parquet auditados como modo local. A competência inicial é a mais
recente e pode ser alterada na barra superior de filtros e contexto.

## Observabilidade

```bash
python scripts/check_platform_health.py
```

O comando retorna código diferente de zero quando qualquer reconciliação falha e grava o último
resultado em `reports/observability/latest_health.json`.

## Verificações antes de release

```bash
ruff check .
ruff format --check .
pytest
dbt build --profiles-dir dbt
```
