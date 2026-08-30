# Silver da banda larga fixa ANATEL 2026

## Objetivo

Validar os registros Bronze, reconciliar a geografia com `dim_municipality`, consolidar o grão
mensal e produzir quarentena auditável. O contrato está em
`config/schemas/fixed_broadband_accesses_silver.yml`.

## Decisão sobre duplicidades

As repetições foram reanalisadas antes da transformação:

- 233.070 chaves possuíam mais de uma linha;
- 219.621 dessas chaves continham valores distintos de `accesses`;
- somente 13.608 ocorrências posteriores à primeira eram cópias exatas de todas as colunas;
- 233.469 linhas eram ocorrências adicionais do grão.

Por isso, remover linhas com `drop_duplicates` descartaria acessos legítimos. A Silver agrupa o
grão e soma `accesses`, mantendo `source_row_count` para demonstrar quantas linhas Bronze deram
origem a cada registro. O resultado não contém nenhuma chave repetida.

## Validações

- ano e mês válidos;
- CNPJ com 14 dígitos;
- velocidade não negativa e coerente com a faixa declarada;
- acessos maiores ou iguais a um;
- domínios de porte, faixa, meio, tipo de pessoa e produto;
- existência do código IBGE em `dim_municipality`;
- correspondência entre código IBGE e UF;
- nome municipal canônico obtido da dimensão.

Foram encontrados 6.304 registros, em 27 códigos IBGE, cujo nome textual da ANATEL diverge da
nomenclatura atual do IBGE. Como código e UF estão corretos, eles não foram rejeitados: o nome
original permanece em `municipality_name_source` e a coluna `municipality_name` recebe o valor
canônico.

## Reconciliação

| Competência | Bronze | Silver | Consolidadas | Acessos Silver |
|---|---:|---:|---:|---:|
| 2026-01 | 698.274 | 659.259 | 39.015 | 55.845.849 |
| 2026-02 | 699.688 | 659.789 | 39.899 | 56.456.202 |
| 2026-03 | 697.255 | 658.794 | 38.461 | 56.879.852 |
| 2026-04 | 700.130 | 660.760 | 39.370 | 57.110.434 |
| 2026-05 | 681.204 | 642.731 | 38.473 | 56.985.020 |
| 2026-06 | 677.552 | 639.301 | 38.251 | 56.609.491 |
| **Total** | **4.154.103** | **3.920.634** | **233.469** | **339.886.848** |

Não houve rejeições. Os seis arquivos de quarentena vazios foram mantidos como evidência da
execução. A soma de acessos antes e depois é idêntica e a segunda execução retornou
`created=false`.

## Verificação posterior independente

Uma nova leitura dos seis Parquets Silver confirmou:

- zero duplicidades no grão;
- zero valores nulos;
- zero códigos, UFs ou nomes canônicos divergentes da dimensão;
- soma de `source_row_count` igual às 4.154.103 linhas Bronze;
- soma de `accesses` igual a 339.886.848;
- tamanho total de 21.434.475 bytes.

O artefato estruturado da verificação está em
`reports/data_quality/fixed_broadband_accesses/silver_validation_2026.json`.
