# Fase 5 — Bronze

## Objetivo

Projetar os campos oficiais do diretório municipal em um contrato estável, preservar sua
semântica e adicionar lineage técnico. Nenhuma regra analítica de limpeza é aplicada aqui.

## Contrato

O schema versionado está em `config/schemas/municipality_directory_bronze.yml`. O grain é uma
linha por município atual do IBGE e a chave candidata permanece `ibge_code`.

Os nomes de origem são projetados para nomes técnicos claros. As divisões legadas
micro/mesorregionais permanecem anuláveis; as regiões imediata/intermediária, UF e macrorregião
são obrigatórias. A coluna residual 100% nula observada no flattening exploratório não integra o
contrato.

## Metadados adicionados

- `_source_file`
- `_ingestion_timestamp`
- `_pipeline_run_id`
- `_sha256`
- `_reference_date`
- `_bronze_timestamp`
- `_schema_version`

## Execução real

| Medida | Resultado |
|---|---:|
| Registros de entrada | 5.571 |
| Registros de saída | 5.571 |
| Registros rejeitados | 0 |
| Colunas | 23 |
| Tamanho RAW JSON | 2.470.036 bytes |
| Tamanho Bronze Parquet | 158.910 bytes |
| Compressão | Zstandard |
| Schema version | 1 |

O Parquet representa aproximadamente 6,43% do tamanho do JSON original, além de preservar tipos
e permitir leitura seletiva. Essa comparação é específica deste dataset e não deve ser
generalizada como taxa fixa.

A segunda execução produziu `created=false` e reutilizou o artefato endereçado pelo hash da
fonte. Nenhum arquivo foi sobrescrito.

## Valores ausentes preservados

Boa Esperança do Norte/MT (`5101837`) permanece com micro/mesorregião legada nula e com região
imediata `Sorriso` válida. Nenhum zero, texto substituto ou hierarquia inventada foi introduzido.

## Schema drift

Se um campo contratado desaparecer do JSON, a transformação falha explicitamente com
`Critical schema drift`. Novos campos da fonte não entram automaticamente no Bronze: exigem
revisão e nova versão do contrato.
