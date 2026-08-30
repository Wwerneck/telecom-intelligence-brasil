# Dicionário — fact_broadband_accesses

**Grão:** uma linha por competência, município, grupo econômico, empresa/CNPJ, porte,
faixa/velocidade, tecnologia, meio de acesso, tipo de pessoa e tipo de produto.

| Coluna | Papel | Descrição |
|---|---|---|
| `date_key` | FK | Primeiro dia da competência em `YYYYMMDD` |
| `municipality_id` | FK | Chave estável de `dim_municipality` |
| `ibge_code` | Degenerada | Código oficial preservado para auditoria |
| `reference_year` | Degenerada | Ano da competência |
| `reference_month` | Degenerada | Mês da competência |
| `economic_group` | Dimensão degenerada | Grupo econômico informado pela ANATEL |
| `company_name` | Dimensão degenerada | Prestadora informada pela ANATEL |
| `company_cnpj` | Dimensão degenerada | CNPJ textual, incluindo zeros à esquerda |
| `provider_size` | Dimensão degenerada | Porte da prestadora |
| `speed_range` | Dimensão degenerada | Faixa oficial de velocidade |
| `speed_mbps` | Dimensão degenerada | Velocidade nominal em Mbps |
| `technology` | Dimensão degenerada | Tecnologia declarada |
| `access_medium` | Dimensão degenerada | Meio físico ou radioelétrico |
| `person_type` | Dimensão degenerada | Pessoa física ou jurídica |
| `product_type` | Dimensão degenerada | Tipo de produto |
| `accesses` | Medida aditiva | Quantidade de acessos na combinação e competência |
| `source_row_count` | Medida de auditoria | Linhas Bronze consolidadas na Silver |
| `_source_file` | Lineage | Artefato RAW oficial |
| `_pipeline_run_id` | Lineage | Execução de ingestão de origem |
| `_sha256` | Lineage | SHA-256 do RAW |
| `_silver_schema_version` | Lineage | Versão do contrato Silver |

`accesses` é aditiva entre dimensões dentro de uma competência, mas somar competências produz
fluxo acumulado de fotografias mensais, não estoque anual.
