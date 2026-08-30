# ADR-003: usar Parquet nas camadas intermediárias

## Context

CSV não preserva tipos e exige leitura ampla, elevando custo em conjuntos grandes.

## Decision

Persistir Bronze e Silver preferencialmente em Parquet comprimido com Zstandard.

## Consequences

Há tipagem, compressão e predicate pushdown; ferramentas precisam suportar Parquet.

## Alternatives

CSV permanece apenas como possível formato oficial de entrada, nunca como padrão intermediário.

