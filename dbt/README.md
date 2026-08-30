# Execução dos marts dbt

Os modelos esperam as tabelas `fact_broadband_accesses`, `dim_municipality` e `dim_date` no
schema PostgreSQL `gold`, conforme `models/sources.yml`.

Após carregar os Parquets Gold no PostgreSQL:

```bash
cp profiles.yml.example profiles.yml
export POSTGRES_PASSWORD=...
dbt build --profiles-dir .
```

Os testes verificam chaves, relacionamentos, reconciliação mensal de acessos e soma de market
share igual a 100%. A implementação de referência local pode ser executada na raiz do projeto
com `python scripts/build_broadband_marts.py`.
