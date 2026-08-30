# Data dictionary — dim_municipality

**Grain:** uma linha por município atual do IBGE na referência da fonte.

| Coluna | Tipo | Descrição | Regra/origem | Nullable |
|---|---|---|---|---|
| municipality_id | bigint | Chave do warehouse | Derivada de `ibge_code`; estável e verificável | Não |
| ibge_code | bigint | Código oficial municipal | API de Localidades do IBGE | Não |
| municipality_name | text | Nome oficial de exibição | IBGE, Unicode NFC | Não |
| municipality_key | text | Chave auxiliar para matching | Nome normalizado; não usar como PK | Não |
| state_id | bigint | Código da UF | IBGE | Não |
| state_code | text | Sigla da UF | IBGE; valores aceitos | Não |
| state_name | text | Nome da UF | IBGE | Não |
| region_id | bigint | Código da macrorregião | IBGE | Não |
| region_code | text | Sigla da macrorregião | IBGE | Não |
| region_name | text | Nome da macrorregião | IBGE | Não |
| immediate_region_id | bigint | Código da região imediata | IBGE | Não |
| immediate_region_name | text | Nome da região imediata | IBGE | Não |
| intermediate_region_id | bigint | Código da região intermediária | IBGE | Não |
| intermediate_region_name | text | Nome da região intermediária | IBGE | Não |
| legacy_microregion_id | bigint | Código da microrregião legada | IBGE | Sim |
| legacy_microregion_name | text | Nome da microrregião legada | IBGE | Sim |
| legacy_mesoregion_id | bigint | Código da mesorregião legada | IBGE | Sim |
| legacy_mesoregion_name | text | Nome da mesorregião legada | IBGE | Sim |
| population | bigint | População residente estimada | SIDRA 6579, variável 9324 | Não na versão enriquecida |
| population_reference_year | integer | Ano da população | SIDRA, atualmente 2025 | Não na versão enriquecida |
| population_source_sha256 | text | Hash do RAW populacional | Manifesto | Não na versão enriquecida |
| source_reference_date | date/text | Referência da aquisição geográfica | Lineage Silver | Não |
| source_sha256 | text | Hash do RAW de origem | Manifesto | Não |
