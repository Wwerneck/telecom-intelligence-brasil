"""Data access and presentation helpers for the Streamlit dashboard."""

from pathlib import Path

import pandas as pd

MART_NAMES = (
    "mart_broadband_national_monthly",
    "mart_broadband_municipality_monthly",
    "mart_broadband_provider_monthly",
    "mart_broadband_technology_monthly",
    "mart_broadband_speed_monthly",
)


def load_local_marts(root: Path) -> dict[str, pd.DataFrame]:
    """Load the latest content-addressed local artifact for every required mart."""
    marts: dict[str, pd.DataFrame] = {}
    for name in MART_NAMES:
        candidates = sorted((root / name).glob("*.parquet"))
        if not candidates:
            raise FileNotFoundError(f"Mart not found: {name}")
        marts[name] = pd.read_parquet(candidates[-1])
    return marts


def available_periods(national: pd.DataFrame) -> list[str]:
    periods = national.assign(
        period=national["reference_year"].astype(str)
        + "-"
        + national["reference_month"].astype(str).str.zfill(2)
    )["period"]
    return sorted(periods.unique().tolist(), reverse=True)


def period_key(period: str) -> int:
    year, month = (int(part) for part in period.split("-"))
    return year * 10_000 + month * 100 + 1


def filter_period(frame: pd.DataFrame, period: str) -> pd.DataFrame:
    return frame.loc[frame["date_key"].eq(period_key(period))].copy()


def format_integer(value: int | float) -> str:
    return f"{value:,.0f}".replace(",", ".")


def format_decimal(value: int | float, digits: int = 2) -> str:
    formatted = f"{value:,.{digits}f}"
    return formatted.replace(",", "_").replace(".", ",").replace("_", ".")
