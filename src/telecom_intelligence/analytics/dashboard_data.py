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

SPEED_RANGE_LABELS = {
    "0Kbps a 512Kbps": "Até 512 Kbps",
    "512kbps a 2Mbps": "De 512 Kbps a 2 Mbps",
    "2Mbps a 12Mbps": "De 2 Mbps a 12 Mbps",
    "12Mbps a 34Mbps": "De 12 Mbps a 34 Mbps",
    "> 34Mbps": "Acima de 34 Mbps",
}

MONTH_ABBREVIATIONS = {
    1: "jan",
    2: "fev",
    3: "mar",
    4: "abr",
    5: "mai",
    6: "jun",
    7: "jul",
    8: "ago",
    9: "set",
    10: "out",
    11: "nov",
    12: "dez",
}


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


def prepare_municipality_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Create a Portuguese, presentation-only municipality table."""
    table = frame[
        [
            "municipality_name",
            "state_code",
            "accesses",
            "accesses_per_100_inhabitants",
            "fiber_share_pct",
            "companies",
        ]
    ].copy()
    table["accesses"] = table["accesses"].map(format_integer)
    table["accesses_per_100_inhabitants"] = table["accesses_per_100_inhabitants"].map(
        format_decimal
    )
    table["fiber_share_pct"] = table["fiber_share_pct"].map(
        lambda value: f"{format_decimal(value)}%"
    )
    table["companies"] = table["companies"].map(format_integer)
    return table.rename(
        columns={
            "municipality_name": "Município",
            "state_code": "UF",
            "accesses": "Acessos",
            "accesses_per_100_inhabitants": "Acessos por 100 habitantes",
            "fiber_share_pct": "Fibra (%)",
            "companies": "Prestadoras",
        }
    )


def prepare_speed_chart(frame: pd.DataFrame) -> pd.DataFrame:
    """Order and localize speed bands for executive presentation."""
    chart = frame[["speed_range", "accesses", "speed_range_share_pct"]].copy()
    chart["Faixa de velocidade"] = chart["speed_range"].map(SPEED_RANGE_LABELS)
    if chart["Faixa de velocidade"].isna().any():
        unknown = chart.loc[chart["Faixa de velocidade"].isna(), "speed_range"].tolist()
        raise ValueError(f"Faixas de velocidade desconhecidas: {unknown}")
    order = {label: position for position, label in enumerate(SPEED_RANGE_LABELS.values())}
    chart["_order"] = chart["Faixa de velocidade"].map(order)
    chart["Participação no total (%)"] = chart["speed_range_share_pct"]
    chart["Participação"] = chart["speed_range_share_pct"].map(
        lambda value: f"{format_decimal(value)}%"
    )
    chart["Acessos formatados"] = chart["accesses"].map(format_integer)
    return chart.sort_values("_order").reset_index(drop=True)


def prepare_provider_chart(frame: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    """Consolidate CNPJs by provider name and prepare an executive ranking."""
    if limit < 1:
        raise ValueError("O limite de prestadoras deve ser positivo")
    chart = (
        frame.groupby("company_name", as_index=False, observed=True)
        .agg(accesses=("accesses", "sum"), market_share_pct=("market_share_pct", "sum"))
        .nlargest(limit, "accesses")
        .sort_values("accesses")
        .reset_index(drop=True)
    )
    chart["Prestadora"] = chart["company_name"]
    chart["Participação"] = chart["market_share_pct"].map(lambda value: f"{format_decimal(value)}%")
    chart["Acessos formatados"] = chart["accesses"].map(format_integer)
    return chart


def prepare_access_medium_chart(frame: pd.DataFrame) -> pd.DataFrame:
    """Aggregate technologies into access media and calculate monthly share."""
    chart = (
        frame.groupby("access_medium", as_index=False, observed=True)["accesses"]
        .sum()
        .sort_values("accesses")
        .reset_index(drop=True)
    )
    total = chart["accesses"].sum()
    if total <= 0:
        raise ValueError("O total de acessos deve ser positivo")
    chart["Meio de acesso"] = chart["access_medium"]
    chart["Participação no total (%)"] = chart["accesses"] / total * 100
    chart["Participação"] = chart["Participação no total (%)"].map(
        lambda value: f"{format_decimal(value)}%"
    )
    chart["Acessos formatados"] = chart["accesses"].map(format_integer)
    return chart


def prepare_evolution_chart(frame: pd.DataFrame) -> pd.DataFrame:
    """Prepare localized labels and tooltips for the national time series."""
    chart = frame.sort_values("date_key").copy()
    chart["Competência"] = chart.apply(
        lambda row: (
            f"{MONTH_ABBREVIATIONS[int(row['reference_month'])]}/{str(int(row['reference_year']))[-2:]}"
        ),
        axis=1,
    )
    chart["Acessos (milhões)"] = chart["accesses"] / 1_000_000
    chart["Acessos formatados"] = chart["accesses"].map(format_integer)
    chart["Rótulo"] = chart["Acessos (milhões)"].map(lambda value: f"{format_decimal(value, 2)} mi")
    chart["Variação mensal"] = chart["accesses_month_over_month_pct"].map(
        lambda value: f"{format_decimal(value)}%" if pd.notna(value) else "Sem mês anterior"
    )
    return chart.reset_index(drop=True)
