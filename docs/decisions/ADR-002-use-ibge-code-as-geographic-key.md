# ADR-002: usar código IBGE como chave geográfica

## Context

Nomes de municípios possuem homônimos, acentos e variações entre fontes.

## Decision

Usar o código oficial do IBGE como chave de integração; nomes são atributos de exibição.

## Consequences

Junções ficam estáveis, mas códigos inválidos ou ausentes devem ir para quarentena.

## Alternatives

Junção por nome e UF foi rejeitada como chave principal por ser frágil.

