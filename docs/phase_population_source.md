# Fonte de população municipal — IBGE/SIDRA

## Recurso validado

- Instituição: IBGE.
- Sistema: SIDRA.
- Tabela: 6579.
- Variável: 9324 — População residente estimada.
- Nível territorial: município (`n6`).
- Período validado: 2025.
- Unidade: Pessoas.
- Formato: JSON UTF-8.

Endpoint configurado:

`https://apisidra.ibge.gov.br/values/t/6579/n6/all/v/9324/p/2025?formato=json`

## Ingestão RAW

| Campo | Resultado |
|---|---|
| HTTP | 200 |
| Tamanho | 1.035.032 bytes |
| SHA-256 | `321710963df3d6e8ad63121f16d3444d79fe5d5d58ab41500af635fb208dcc86` |
| Linhas municipais | 5.571 |
| Linhas descritivas | 1 |
| Linhas no manifesto após duas execuções | 1 |

A primeira posição da resposta é um dicionário de rótulos, não uma observação. O parser separa
explicitamente esse cabeçalho antes de medir ou transformar os dados.

## Profiling

| Verificação | Resultado |
|---|---:|
| Códigos IBGE únicos | 5.571 |
| Códigos duplicados | 0 |
| Códigos inválidos | 0 |
| Valores não numéricos | 0 |
| Valores negativos | 0 |
| Códigos ausentes na geografia | 0 |
| Municípios geográficos sem população | 0 |
| Menor valor observado | 856 |
| Maior valor observado | 11.904.961 |

Mínimo e máximo são observações da fonte e ainda não constituem análise de negócio. Nenhum
outlier será removido: grandes diferenças populacionais entre municípios são plausíveis.

## Próxima transformação

O próximo build criará Bronze e Silver específicas para população, validará `D2C=9324`, ano,
unidade e parsing numérico, e só então enriquecerá `dim_municipality`. A junção será exclusivamente
por código IBGE; nomes com o sufixo da UF não participarão da chave.
