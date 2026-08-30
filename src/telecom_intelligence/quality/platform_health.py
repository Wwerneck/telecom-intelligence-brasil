"""Operational checks across persisted broadband layers and marts."""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq


@dataclass(frozen=True)
class HealthCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class PlatformHealth:
    status: str
    checked_at: str
    checks: list[HealthCheck]

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "checked_at": self.checked_at,
            "checks": [asdict(check) for check in self.checks],
        }


def _rows(paths: list[Path]) -> int:
    return sum(pq.read_metadata(path).num_rows for path in paths)


def check_platform_health(root: Path) -> PlatformHealth:
    """Reconcile the persisted pipeline without loading wide fact tables."""
    bronze = sorted(
        (root / "data/bronze/dataset=fixed_broadband_accesses").glob("year=*/month=*/*.parquet")
    )
    silver = sorted(
        (root / "data/silver/dataset=fixed_broadband_accesses").glob("year=*/month=*/*.parquet")
    )
    fact = sorted((root / "data/gold/fact_broadband_accesses").glob("year=*/month=*/*.parquet"))
    quarantine = sorted(
        (root / "data/quarantine/invalid_broadband").glob("year=*/month=*/*.parquet")
    )
    national_paths = sorted(
        (root / "data/gold/marts/mart_broadband_national_monthly").glob("*.parquet")
    )
    checks: list[HealthCheck] = []

    partitions_ok = len(bronze) == len(silver) == len(fact) == len(quarantine) == 6
    checks.append(
        HealthCheck(
            "monthly_partitions",
            partitions_ok,
            f"bronze/silver/fact={len(bronze)}/{len(silver)}/{len(fact)}",
        )
    )
    if partitions_ok:
        bronze_rows = _rows(bronze)
        silver_source_rows = sum(
            int(pd.read_parquet(path, columns=["source_row_count"])["source_row_count"].sum())
            for path in silver
        )
        fact_source_rows = sum(
            int(pd.read_parquet(path, columns=["source_row_count"])["source_row_count"].sum())
            for path in fact
        )
        lineage_ok = bronze_rows == silver_source_rows == fact_source_rows
        checks.append(
            HealthCheck(
                "row_lineage_reconciliation",
                lineage_ok,
                f"bronze/silver/fact_source={bronze_rows}/{silver_source_rows}/{fact_source_rows}",
            )
        )
        fact_accesses = sum(
            int(pd.read_parquet(path, columns=["accesses"])["accesses"].sum()) for path in fact
        )
        national_accesses = (
            int(pd.read_parquet(national_paths[-1], columns=["accesses"])["accesses"].sum())
            if national_paths
            else -1
        )
        checks.append(
            HealthCheck(
                "access_reconciliation",
                fact_accesses == national_accesses,
                f"fact/national={fact_accesses}/{national_accesses}",
            )
        )
        quarantine_rows = _rows(quarantine)
        checks.append(
            HealthCheck("quarantine_empty", quarantine_rows == 0, f"rows={quarantine_rows}")
        )
    else:
        checks.extend(
            [
                HealthCheck("row_lineage_reconciliation", False, "partitions unavailable"),
                HealthCheck("access_reconciliation", False, "partitions unavailable"),
                HealthCheck("quarantine_empty", False, "partitions unavailable"),
            ]
        )
    status = "healthy" if all(check.passed for check in checks) else "unhealthy"
    return PlatformHealth(status, datetime.now(UTC).isoformat(), checks)
