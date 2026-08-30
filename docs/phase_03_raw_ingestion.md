# Fase 3 — Raw Ingestion

## Implementação

A ingestão RAW usa streaming HTTP, retry exponencial somente para falhas transitórias,
SHA-256 calculado durante o download, arquivo temporário e promoção atômica para o destino.
O original não é alterado após sua persistência.

O manifesto local SQLite mantém `source`, `dataset`, `reference_date`, `source_file`,
`raw_path`, `download_timestamp`, `file_size`, `sha256`, `status`, `records_loaded` e
`pipeline_run_id`. A restrição única `(dataset, reference_date, sha256)` garante que o mesmo
conteúdo não seja registrado duas vezes.

## Execução oficial validada

Em 28/08/2026, o diretório municipal oficial do IBGE foi ingerido com:

| Campo | Resultado |
|---|---|
| Dataset | `municipality_directory` |
| Referência de aquisição | `2026-08-28` |
| Tamanho | 2.470.036 bytes |
| Registros JSON verificados | 5.571 |
| SHA-256 | `d9eec8439bc8c5dc2f7db6332a8e5569f5a3f637988e26aebc513412d4069d5c` |
| Status | `downloaded` |
| Linhas no manifesto após duas execuções | 1 |

A segunda execução recebeu o mesmo conteúdo, removeu o download temporário e retornou
`downloaded=false`. O RAW existente permaneceu inalterado.

## Limites desta fase

`records_loaded` permanece nulo no manifesto RAW porque interpretar e contar registros pertence
ao profiling/Bronze, não ao download. O arquivo e o banco de manifesto são artefatos locais
ignorados pelo Git; somente código, contratos e evidências auditáveis são versionados.
