# ADR-001: usar arquitetura Medallion

## Context

As fontes oficiais exigem preservação do original, tratamento progressivo e rastreabilidade.

## Decision

Separar dados em RAW, Bronze, Silver e Gold, com Quarantine paralela para rejeições.

## Consequences

Transformações ficam auditáveis e reprocessáveis, ao custo de mais armazenamento e contratos.

## Alternatives

Transformação direta para o warehouse foi rejeitada por reduzir rastreabilidade e recuperação.

