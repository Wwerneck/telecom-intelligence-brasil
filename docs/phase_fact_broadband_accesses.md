# Fact de acessos de banda larga fixa

## Modelo

`fact_broadband_accesses` foi construída exclusivamente a partir da Silver validada. O grão
mantém as dimensões analíticas comprovadas pela fonte e usa:

- `municipality_id` como FK de `dim_municipality`;
- `date_key` como FK da dimensão mensal de datas;
- `accesses` como medida aditiva dentro da competência;
- `source_row_count` como medida de rastreabilidade.

As categorias de prestadora, velocidade, tecnologia, meio, pessoa e produto permanecem como
dimensões degeneradas. Dimensões separadas só deverão ser criadas se houver atributos próprios,
histórico ou necessidade comprovada de governança.

## Proteções contra fan-out

O join municipal exige cardinalidade `many_to_one`, e a transformação falha se
`municipality_id` não for único. O build também falha diante de:

- repetição do grão Silver antes do join;
- ausência de FK municipal ou temporal;
- repetição do grão da fact após o join;
- diferença na soma de acessos;
- diferença na soma de `source_row_count`.

## Resultado real

| Verificação | Resultado |
|---|---:|
| Linhas Silver | 3.920.634 |
| Linhas fact | 3.920.634 |
| Linhas RAW/Bronze representadas | 4.154.103 |
| Acessos Silver | 339.886.848 |
| Acessos fact | 339.886.848 |
| Chaves duplicadas | 0 |
| Nulos | 0 |
| FKs municipais ausentes | 0 |
| FKs temporais ausentes | 0 |
| Tamanho dos seis Parquets | 16.981.686 bytes |

A dimensão temporal sustentada pela fonte contém seis registros, com chaves de `20260101` a
`20260601`. A data representa o primeiro dia convencional da competência mensal, não o dia de
coleta.

Os arquivos são particionados por ano/mês, carregam `layer=gold`,
`model=fact_broadband_accesses` e o SHA-256 de origem. A segunda execução retornou
`created=false`.

O resultado estruturado da auditoria está em
`reports/data_quality/fixed_broadband_accesses/fact_validation_2026.json`.
