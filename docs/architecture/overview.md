# Arquitetura da plataforma

## Objetivo

Separar aquisição, preservação, tratamento e consumo para que cada indicador possa ser
rastreado até um arquivo oficial, sua execução de pipeline e suas regras de qualidade.

## Responsabilidades por camada

| Camada | Responsabilidade | Alteração do dado de origem |
|---|---|---|
| RAW | Arquivo original, hash e metadados de aquisição | Nenhuma; imutável |
| Bronze | Schema minimamente normalizado e metadados técnicos | Mínima |
| Silver | Tipagem, harmonização, validação e deduplicação governada | Controlada e auditável |
| Gold | Modelo dimensional, métricas e marts de negócio | Agregações documentadas |
| Quarantine | Registros rejeitados com motivo e execução | Não participa dos KPIs |

## Escolhas tecnológicas

- MinIO representa armazenamento compatível com S3 sem exigir nuvem na versão inicial.
- Parquet oferece tipagem, compressão e leitura seletiva nas camadas intermediárias.
- PostgreSQL serve a camada analítica e o dashboard, não como depósito dos arquivos brutos.
- dbt mantém transformações SQL, testes, documentação e lineage da camada analítica.
- Airflow orquestra dependências, retries transitórios e backfills parametrizados.
- PySpark será empregado apenas em transformações cujo volume ou paralelismo o justifique.

## Princípios operacionais

RAW é imutável; configurações e URLs ficam centralizadas; falhas críticas de schema interrompem
o pipeline; rejeições são explicadas; a combinação dataset, competência, hash e chave de negócio
sustenta idempotência; segredos são fornecidos somente por ambiente.

