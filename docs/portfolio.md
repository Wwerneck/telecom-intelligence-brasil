# Telecom Intelligence Brasil — visão de portfólio

## Produto

Plataforma de dados que transforma fontes oficiais da ANATEL e do IBGE em inteligência mensal
de banda larga fixa, com rastreabilidade até o arquivo RAW e validações em todas as camadas.

## Entrega do MVP

- extração seletiva de um membro de ZIP remoto sem baixar o arquivo completo;
- RAW imutável e manifesto idempotente;
- profiling incremental de 4.154.103 registros;
- Bronze particionada e Silver com deduplicação governada;
- dimensão municipal com população IBGE 2025;
- fact com 3.920.634 chaves únicas e 339.886.848 acessos reconciliados;
- cinco marts mensais em Parquet e PostgreSQL/dbt;
- dashboard Streamlit e health check operacional;
- testes unitários, integração ponta a ponta, dbt e CI.

## Decisões de qualidade

As 233.469 ocorrências adicionais do grão não foram simplesmente apagadas. Como a maioria tinha
medidas distintas, elas foram agregadas por soma e registradas em `source_row_count`. Nomes
municipais históricos da ANATEL foram preservados e canonizados pelo código IBGE. População é
associada somente após agregação municipal para impedir fan-out no denominador.

## Resultado validado

Em junho de 2026, a fonte registra 56.609.491 acessos, densidade de 26,5248 acessos por 100
habitantes, 80,3633% em fibra e 94,9679% acima de 34 Mbps. Essas métricas representam acessos e
fotografias mensais; não equivalem a pessoas conectadas nem devem ser somadas como estoque anual.

## Evolução futura

O mesmo padrão pode ser aplicado a acessos móveis, estações licenciadas, reclamações e outros
indicadores de conectividade após validação das respectivas fontes e grains.
