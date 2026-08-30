# Fase 6 — Silver

## Objetivo

Produzir uma referência municipal tipada, padronizada e validada, separando registros aprovados
de rejeições explicadas. O processamento não usa `fillna(0)`, `dropna()` ou deduplicação cega.

## Transformações controladas

1. Validação do contrato e das colunas obrigatórias.
2. Normalização Unicode NFC, espaços e caracteres invisíveis nos campos de exibição.
3. Preservação integral de acentos e capitalização nos nomes exibidos.
4. Criação de `municipality_key`, em ASCII e snake_case, apenas para matching.
5. Validação do código IBGE com sete dígitos.
6. Validação de UF e macrorregião contra valores aceitos.
7. Detecção de duplicidade da chave antes de qualquer remoção.
8. Separação de rejeições com motivo, fonte, execução e timestamp.

## Execução real

| Etapa | Antes | Depois | Rejeitados |
|---|---:|---:|---:|
| Leitura e schema | 5.571 | 5.571 | 0 |
| Normalização textual | 5.571 | 5.571 | 0 |
| Chave de matching | 5.571 | 5.571 | 0 |
| Validação geográfica | 5.571 | 5.571 | 0 |
| Validação de duplicidades | 5.571 | 5.571 | 0 |

O resultado contém 26 colunas, 27 UFs, cinco macrorregiões, nenhuma chave nula e nenhuma
duplicidade de código IBGE. O arquivo Silver possui 200.262 bytes em Parquet/Zstandard.

A quarentena foi materializada mesmo sem rejeições, com zero linhas e schema próprio. Isso evita
confundir “pipeline não executado” com “pipeline executado sem erros”.

## Ausências classificadas

Os quatro atributos legados de micro/mesorregião de Boa Esperança do Norte/MT continuam nulos e
são classificados como `not_available`. A região imediata `Sorriso`, UF e macrorregião estão
válidas. Nenhum dado foi inferido.

## Idempotência

A primeira execução criou Silver e Quarantine. A segunda retornou `created=false` para Silver,
sem sobrescrever o conteúdo endereçado pelo SHA-256 de origem.

## Evidências

- `reports/data_quality/municipality_directory/silver_transformation_audit.json`
- `reports/data_quality/municipality_directory/missing_values_strategy.csv`
- `data/quarantine/invalid_municipality/` (artefato local não versionado)
