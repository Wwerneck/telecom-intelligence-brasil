from pathlib import Path

import pandas as pd

from telecom_intelligence.quality.platform_health import check_platform_health


def write_partition(root: Path, layer: str, month: int, frame: pd.DataFrame) -> None:
    if layer == "quarantine":
        path = root / "data/quarantine/invalid_broadband" / "year=2026" / f"month={month:02d}"
    elif layer == "gold":
        path = root / "data/gold/fact_broadband_accesses" / "year=2026" / f"month={month:02d}"
    else:
        path = (
            root
            / f"data/{layer}/dataset=fixed_broadband_accesses"
            / "year=2026"
            / f"month={month:02d}"
        )
    path.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path / "sha256=test.parquet", index=False)


def test_platform_health_reconciles_layers(tmp_path: Path) -> None:
    for month in range(1, 7):
        write_partition(tmp_path, "bronze", month, pd.DataFrame({"accesses": [10, 15]}))
        write_partition(tmp_path, "silver", month, pd.DataFrame({"source_row_count": [2]}))
        write_partition(
            tmp_path, "gold", month, pd.DataFrame({"source_row_count": [2], "accesses": [25]})
        )
        write_partition(tmp_path, "quarantine", month, pd.DataFrame({"accesses": []}))
    mart = tmp_path / "data/gold/marts/mart_broadband_national_monthly"
    mart.mkdir(parents=True)
    pd.DataFrame({"accesses": [25] * 6}).to_parquet(mart / "sha256=test.parquet", index=False)

    health = check_platform_health(tmp_path)

    assert health.status == "healthy"
    assert all(check.passed for check in health.checks)
