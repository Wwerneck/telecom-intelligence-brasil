# ADR-004: usar dbt na camada analítica

## Context

Métricas e marts SQL precisam de testes, documentação e lineage reproduzíveis.

## Decision

Usar dbt para staging SQL, modelos intermediários e marts no PostgreSQL.

## Consequences

Regras analíticas ficam versionadas; Python/PySpark continuam responsáveis pela Silver.

## Alternatives

SQL avulso e transformações analíticas somente em Python foram rejeitados por menor governança.

