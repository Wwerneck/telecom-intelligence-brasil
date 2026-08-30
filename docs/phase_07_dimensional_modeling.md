# Fase 7 — Modelagem Dimensional

## Escopo atual

A modelagem foi limitada às dimensões sustentadas por fontes já ingeridas e validadas. Não foram
criadas facts vazias, acessos de telecom sintéticos ou população estimada pelo projeto.

## dim_municipality

**Grain:** uma linha por município atual do IBGE na referência geográfica da fonte.

**Chave do warehouse:** `municipality_id`, derivada diretamente do código IBGE. Nesta dimensão
tipo 1, isso oferece estabilidade e rastreabilidade sem uma sequência dependente da ordem de
carga. `ibge_code` é preservado como chave oficial de negócio.

Resultado validado:

| Medida | Resultado |
|---|---:|
| Linhas | 5.571 |
| `municipality_id` únicos | 5.571 |
| Códigos IBGE únicos | 5.571 |
| UFs | 27 |
| Macrorregiões | 5 |
| População preenchida | 0 |

As colunas `population` e `population_reference_year` foram reservadas e permanecem nulas. Elas
só serão populadas após ingestão de uma referência oficial do IBGE com ano explicitamente
definido.

## dim_date

**Grain:** uma linha por data de referência evidenciada pelos datasets processados.

A execução atual contém somente `2026-08-28`, data da aquisição do diretório geográfico, com
`date_key=20260828`, terceiro trimestre e competência `2026-08`. A dimensão será expandida à
medida que fontes mensais oficiais forem integradas.

## Facts

`fact_broadband_accesses` passou a ser suportada após ingestão, profiling, Bronze e Silver da
fonte oficial. Seu desenho e sua reconciliação estão em
`docs/phase_fact_broadband_accesses.md`. As facts de mobilidade, estações, reclamações e
conectividade continuam pendentes até que suas respectivas fontes e grains sejam validados.

## Integridade e idempotência

- O build falha diante de código IBGE duplicado.
- Todas as linhas preservam a referência e SHA-256 da fonte.
- Os Parquets Gold carregam metadados `layer=gold` e o nome do modelo.
- A segunda execução retornou `created=false` para os dois artefatos.

Os dicionários completos estão em `docs/data_dictionary/dim_municipality.md` e
`docs/data_dictionary/dim_date.md`.
