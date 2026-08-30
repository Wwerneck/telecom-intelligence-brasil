# Bronze da banda larga fixa ANATEL 2026

## Objetivo

Converter incrementalmente o CSV RAW oficial em Parquet tipado e particionado, preservando
todas as linhas e adicionando lineage técnico. Não há limpeza, deduplicação ou agregação nesta
camada.

O contrato versionado está em
`config/schemas/fixed_broadband_accesses_bronze.yml`.

## Execução oficial

| Medida | Resultado |
|---|---:|
| Registros de entrada | 4.154.103 |
| Registros de saída | 4.154.103 |
| Registros rejeitados | 0 |
| Partições mensais | 6 |
| Colunas de negócio | 16 |
| Colunas técnicas | 7 |
| Tamanho RAW | 604.746.623 bytes |
| Tamanho total Bronze | 38.568.829 bytes |
| Compressão | Zstandard |
| Schema version | 1 |

As partições seguem `dataset=fixed_broadband_accesses/year=2026/month=MM` e cada arquivo é
endereçado pelos primeiros 16 caracteres do SHA-256 do RAW.

## Reconciliação mensal

| Competência | Linhas | Acessos |
|---|---:|---:|
| 2026-01 | 698.274 | 55.845.849 |
| 2026-02 | 699.688 | 56.456.202 |
| 2026-03 | 697.255 | 56.879.852 |
| 2026-04 | 700.130 | 57.110.434 |
| 2026-05 | 681.204 | 56.985.020 |
| 2026-06 | 677.552 | 56.609.491 |
| **Total das fotografias mensais** | **4.154.103** | **339.886.848** |

O total reconcilia exatamente com o profiling do RAW. Ele não representa um estoque anual e
não deve ser publicado como tal.

## Tipagem e preservação

- ano e mês usam inteiros compactos;
- código IBGE é inteiro de 32 bits;
- CNPJ permanece texto, preservando zeros à esquerda;
- velocidade com vírgula decimal é representada em Mbps como `float64`;
- acessos são `int64`;
- dimensões textuais mantêm os valores oficiais.

A segunda execução encontrou os seis artefatos pelo hash da fonte, somou seus metadados e
retornou `created=false`, sem reler o CSV ou sobrescrever os Parquets.

## Próximo passo

Na Silver, validar domínios e integridade municipal, agregar as repetições do grão pela soma de
`accesses`, produzir quarentena quando necessário e registrar reconciliação antes/depois.
