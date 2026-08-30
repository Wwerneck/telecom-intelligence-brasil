# Descoberta — Banda Larga Fixa ANATEL

## Recurso oficial validado

O arquivo consolidado oficial respondeu HTTP 200 em 28/08/2026:

`https://www.anatel.gov.br/dadosabertos/paineis_de_dados/acessos/acessos_banda_larga_fixa.zip`

| Metadado HTTP | Valor |
|---|---|
| Content-Type | `application/x-zip-compressed` |
| Content-Length | 1.029.180.610 bytes |
| Last-Modified | 01/08/2026 10:32:27 GMT |

O glossário oficial informa CSVs desde 2007, consolidações por empresa, município, tecnologia,
velocidade, grupo, região e UF, e uma opção `Total` sem consolidação. Também alerta que os dados
são declarados pelas prestadoras e podem sofrer correções.

## Descoberta seletiva do ZIP

Para não baixar 1,03 GB sem conhecer o conteúdo, foram lidos somente 128 KB do final do arquivo e
3.240 bytes do diretório central usando HTTP Range. O ZIP possui 27 membros. O inventário
completo está em `reports/data_quality/anatel_broadband_archive_inventory.csv`.

O recorte selecionado para a primeira fact é:

| Membro | Comprimido | Descomprimido |
|---|---:|---:|
| `Acessos_Banda_Larga_Fixa_2026.csv` | 67.253.578 bytes | 604.746.623 bytes |

O arquivo de colunas de 2026 tem 10.969.815 bytes comprimidos e será usado para validar schema e
grain. O ano de 2025 tem 141.346.036 bytes comprimidos e ficará para backfill após o pipeline
2026 ser aprovado.

## Recursos rejeitados

URLs candidatas de CSV mensal responderam HTTP 200 com `text/html; charset=windows-1252` e uma
página de bloqueio, não CSV. Elas não foram habilitadas. URLs anuais diretas ao lado do ZIP
responderam HTTP 404.

## Decisão de engenharia

O pipeline deverá extrair membros específicos por HTTP Range, preservar os bytes originais do
membro como RAW, registrar URL do contêiner, nome do membro, intervalo, tamanho e SHA-256, e
processar o CSV em chunks. Isso evita transferir anos fora do escopo e carregar aproximadamente
605 MB integralmente na memória.
