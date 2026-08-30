# Extrator seletivo de ZIP remoto — ANATEL

## Implementação

O extrator lê o registro EOCD e o diretório central por HTTP Range, localiza o membro solicitado
e transfere somente seu fluxo comprimido. A descompressão Deflate ocorre em streaming, com
validação simultânea de tamanho, CRC-32 e SHA-256.

Metadados adicionais registrados no manifesto:

- URL oficial do arquivo-contêiner;
- nome do membro;
- tamanho comprimido;
- CRC-32 declarado pelo ZIP;
- tamanho extraído;
- SHA-256 do CSV RAW.

A idempotência é verificada antes da transferência do membro por dataset, referência, URL,
membro, CRC-32 e tamanho comprimido. Uma alteração real do membro produz nova carga; uma
reexecução sem alteração consulta apenas os pequenos metadados remotos.

## Execução oficial 2026

| Campo | Resultado |
|---|---|
| Dataset | `fixed_broadband_accesses` |
| Membro | `Acessos_Banda_Larga_Fixa_2026.csv` |
| Transferência comprimida | 67.253.578 bytes |
| RAW extraído | 604.746.623 bytes |
| CRC-32 | `cadf546b` |
| SHA-256 | `73675e395662ad8d6d2dc7e6de7b9c9607e0fe1021f28e5619a91d5d65cf93bc` |
| Segunda execução | `downloaded=false` |
| Linhas no manifesto | 1 para o dataset/período |

Os outros anos do ZIP não foram transferidos. O arquivo RAW é ignorado pelo Git e não será
alterado pelas próximas camadas.

## Próximo passo

O CSV de aproximadamente 605 MB será perfilado em chunks. Encoding, delimitador, colunas,
competências, códigos IBGE, valores numéricos, duplicidades e grain serão determinados antes da
construção da Bronze.
