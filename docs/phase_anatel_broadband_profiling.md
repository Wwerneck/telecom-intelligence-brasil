# Profiling da banda larga fixa ANATEL 2026

## Escopo

O CSV RAW oficial foi lido incrementalmente, sem modificação e sem carga integral em memória.
O perfil reproduzível está em
`reports/data_quality/fixed_broadband_accesses/profile_2026.json`.

## Resultado observado

| Verificação | Resultado |
|---|---:|
| Linhas | 4.154.103 |
| Colunas | 16 |
| Competências | 2026-01 a 2026-06 |
| Municípios/códigos IBGE distintos | 5.571 |
| Códigos fora da dimensão municipal | 0 |
| Municípios da dimensão ausentes na fonte | 0 |
| Campos nulos | 0 |
| Anos, meses, UFs ou códigos IBGE inválidos | 0 |
| Velocidades não numéricas ou negativas | 0 |
| Acessos não numéricos, negativos ou iguais a zero | 0 |
| Soma de acessos nas seis competências | 339.886.848 |
| Menor/maior valor de acessos por registro | 1 / 658.092 |

A soma representa seis fotografias mensais e não deve ser publicada como estoque anual. KPIs de
estoque devem manter a competência ou selecionar uma competência específica.

## Grão encontrado

O grão candidato usa todas as 15 colunas descritivas, incluindo a velocidade numérica; `Acessos`
é a medida. Mesmo nesse grão há 233.469 ocorrências posteriores à primeira com a mesma chave.
A Bronze deve preservar todas as linhas e a Silver deve agregar essas repetições pela soma de
`Acessos`, mantendo contagens antes/depois como evidência de qualidade.

## Próximo passo

Construir o contrato Bronze, converter tipos e nomes de colunas para o padrão interno e gravar
Parquet particionado por ano e mês. Depois, validar a agregação do grão na Silver e sua cobertura
referencial contra `dim_municipality`.
