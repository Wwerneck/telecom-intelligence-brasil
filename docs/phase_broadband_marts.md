# Marts e KPIs de banda larga fixa

## Escopo

Foram construídos cinco marts mensais sobre `fact_broadband_accesses`:

- `mart_broadband_national_monthly`;
- `mart_broadband_municipality_monthly`;
- `mart_broadband_provider_monthly`;
- `mart_broadband_technology_monthly`;
- `mart_broadband_speed_monthly`.

Os modelos dbt estão em `dbt/models/marts`. A lógica foi inicialmente auditada por uma
implementação de referência sobre os Parquets Gold e depois executada no PostgreSQL 16. O
`dbt build` concluiu 7 modelos e 21 testes com `PASS=28`, sem avisos ou erros.

## Regras contra dupla contagem

- a fact é agregada antes de qualquer join com população;
- `dim_municipality` é exigida com uma única linha e população preenchida por município;
- a população nacional é somada diretamente da dimensão, uma única vez;
- participações usam o total da mesma competência como denominador;
- crescimento mensal usa `lag(accesses)` ordenado por `date_key`;
- janeiro possui crescimento nulo por não existir dezembro na fonte ingerida.

## Reconciliação

| Mart | Linhas | Grão duplicado |
|---|---:|---:|
| Nacional mensal | 6 | 0 |
| Municipal mensal | 33.423 | 0 |
| Prestadora mensal | 60.942 | 0 |
| Tecnologia mensal | 502 | 0 |
| Faixa de velocidade mensal | 30 | 0 |

Os cinco marts reconciliam com a fact. A soma nacional das seis fotografias é 339.886.848
acessos. As participações por prestadora, tecnologia e faixa somam 100% em cada competência.

## KPIs de junho de 2026

| Indicador | Valor |
|---|---:|
| Acessos | 56.609.491 |
| Variação mensal | -0,6590% |
| Municípios com observação | 5.571 |
| CNPJs de prestadoras | 9.524 |
| População IBGE 2025 | 213.421.037 |
| Acessos por 100 habitantes | 26,5248 |
| Acessos em fibra | 45.493.277 |
| Participação da fibra | 80,3633% |
| Acessos acima de 34 Mbps | 53.760.862 |
| Participação acima de 34 Mbps | 94,9679% |

`Acessos por 100 habitantes` é uma densidade de linhas sobre população, não uma porcentagem de
pessoas conectadas. O numerador inclui os tipos de pessoa e produto presentes na fonte; filtros
mais restritos devem ser nomeados explicitamente em análises futuras.

## Evidência

O relatório estruturado está em
`reports/data_quality/fixed_broadband_accesses/marts_validation_2026.json`. A segunda execução
local retornou `created=false`.
