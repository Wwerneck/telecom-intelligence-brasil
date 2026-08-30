# População — Bronze, Silver e enriquecimento dimensional

## Bronze

A primeira posição do JSON SIDRA foi classificada como cabeçalho descritivo, não como registro
rejeitado. As 5.571 observações foram projetadas preservando códigos, rótulos e valor textual de
origem, além dos metadados técnicos padrão.

## Silver

Foram tipados `ibge_code`, `population` e `population_reference_year`. As regras verificam:

- código IBGE com sete dígitos;
- população numérica e não negativa;
- unidade `Pessoas`;
- variável `9324`;
- ano 2025;
- unicidade de código IBGE + ano.

Resultado: 5.571 entradas, 5.571 saídas e zero registros na quarentena. A segunda execução de
Bronze e Silver retornou `created=false`.

## dim_municipality enriquecida

A junção foi executada exclusivamente por `ibge_code`, com validação `one_to_one` e falha
explícita em caso de lacuna. A dimensão enriquecida possui:

| Medida | Resultado |
|---|---:|
| Municípios | 5.571 |
| Populações nulas | 0 |
| Ano populacional | 2025 |
| Menor população observada | 856 |
| Maior população observada | 11.904.961 |

A versão anterior, somente geográfica, foi preservada. A nova versão usa um hash de lineage
calculado sobre os hashes das duas fontes e foi gravada como
`sha256=9edd8e0d533a99d0.parquet`. Reexecutar com os mesmos upstreams não a sobrescreve.

Esses valores são observações oficiais, mas ainda não devem ser usados para afirmar causalidade
ou produzir métricas de telecom antes da ingestão das facts correspondentes.
