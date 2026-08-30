# Fase 4 — Data Profiling

## Dataset analisado

Diretório municipal obtido diretamente da API de Localidades do IBGE, referência de aquisição
28/08/2026. O arquivo RAW permaneceu inalterado.

## Resultados

| Verificação | Resultado |
|---|---:|
| Linhas | 5.571 |
| Colunas após flattening | 23 |
| Códigos IBGE únicos | 5.571 |
| Nomes municipais únicos | 5.298 |
| Duplicatas completas | 0 |
| Duplicatas de código IBGE | 0 |
| UFs inválidas | 0 |
| Regiões inválidas | 0 |
| Violações geográficas críticas | 0 |
| Menor código observado | 1100015 |
| Maior código observado | 5300108 |
| Comprimento dos nomes | 3 a 32 caracteres |

Nomes não são únicos nacionalmente: 5.571 registros produzem 5.298 nomes distintos. Isso é
esperado pela existência de municípios homônimos e confirma que o nome não pode ser usado como
chave geográfica.

## Valores ausentes

As hierarquias atuais de região imediata, região intermediária, UF e macrorregião estão
completas. As colunas da divisão legada de microrregião/mesorregião têm um valor ausente
(0,01795%), correspondente a **Boa Esperança do Norte/MT**, código IBGE `5101837`.

Esse registro não é rejeitado: o município possui a hierarquia geográfica atual completa. O
ausente é classificado como “não disponível na divisão regional legada da fonte”, não como zero
nem como município inválido.

A coluna adicional `microrregiao`, criada pelo flattening devido ao objeto nulo desse registro,
é 100% nula e não representa um atributo analítico separado. Na Bronze, o schema será projetado
explicitamente para evitar essa coluna residual.

## Distribuição regional

| Região | Municípios |
|---|---:|
| Centro-Oeste | 468 |
| Nordeste | 1.794 |
| Norte | 450 |
| Sudeste | 1.668 |
| Sul | 1.191 |

## Artefatos

- `municipality_profile_summary.json`: resumo estrutural e distribuições.
- `municipality_column_profile.csv`: dtype, nulos, cardinalidade, mínimos/máximos e comprimentos.
- `missing_values_report.csv`: classificação quantitativa das ausências.
- `municipality_duplicate_keys.csv`: evidência de duplicidade da chave, atualmente vazia.
- `municipality_quality_issues.csv`: violações geográficas, atualmente vazio.

Os arquivos ficam em `reports/data_quality/municipality_directory/` e são produzidos novamente
por `python scripts/profile_ibge_municipalities.py`.

## Decisão para a próxima fase

A Bronze projetará somente os campos contratados, preservará os dois conjuntos de hierarquias
regionais com nomes explícitos e adicionará metadados técnicos. Nenhum `fillna(0)`, `dropna()` ou
`drop_duplicates()` será aplicado.
