from pathlib import Path

import pandas as pd

from telecom_intelligence.analytics.dashboard_data import (
    available_periods,
    filter_period,
    format_decimal,
    format_integer,
    load_local_marts,
    prepare_access_medium_chart,
    prepare_evolution_chart,
    prepare_municipality_table,
    prepare_provider_chart,
    prepare_speed_chart,
)


def test_period_helpers_sort_and_filter() -> None:
    frame = pd.DataFrame(
        [
            {"date_key": 20260101, "reference_year": 2026, "reference_month": 1},
            {"date_key": 20260201, "reference_year": 2026, "reference_month": 2},
        ]
    )
    assert available_periods(frame) == ["2026-02", "2026-01"]
    assert filter_period(frame, "2026-02")["date_key"].tolist() == [20260201]


def test_portuguese_number_formatting() -> None:
    assert format_integer(56_609_491) == "56.609.491"
    assert format_decimal(26.524794) == "26,52"


def test_loader_requires_all_marts(tmp_path: Path) -> None:
    try:
        load_local_marts(tmp_path)
    except FileNotFoundError as error:
        assert "Mart not found" in str(error)
    else:
        raise AssertionError("Expected missing mart failure")


def test_municipality_table_has_portuguese_labels_and_formats() -> None:
    source = pd.DataFrame(
        [
            {
                "municipality_name": "São Paulo",
                "state_code": "SP",
                "accesses": 4_740_591,
                "accesses_per_100_inhabitants": 39.8203,
                "fiber_share_pct": 63.1467,
                "companies": 907,
            }
        ]
    )

    table = prepare_municipality_table(source)

    assert table.columns.tolist() == [
        "Município",
        "UF",
        "Acessos",
        "Acessos por 100 habitantes",
        "Fibra (%)",
        "Prestadoras",
    ]
    assert table.loc[0, "Acessos"] == "4.740.591"
    assert table.loc[0, "Acessos por 100 habitantes"] == "39,82"
    assert table.loc[0, "Fibra (%)"] == "63,15%"


def test_speed_chart_is_ordered_and_localized() -> None:
    source = pd.DataFrame(
        [
            {"speed_range": "> 34Mbps", "accesses": 95, "speed_range_share_pct": 95.0},
            {"speed_range": "0Kbps a 512Kbps", "accesses": 5, "speed_range_share_pct": 5.0},
        ]
    )

    chart = prepare_speed_chart(source)

    assert chart["Faixa de velocidade"].tolist() == ["Até 512 Kbps", "Acima de 34 Mbps"]
    assert chart["Participação"].tolist() == ["5,00%", "95,00%"]
    assert chart["Acessos formatados"].tolist() == ["5", "95"]


def test_provider_chart_consolidates_cnpjs_and_ranks() -> None:
    source = pd.DataFrame(
        [
            {"company_name": "Empresa A", "accesses": 60, "market_share_pct": 30.0},
            {"company_name": "Empresa A", "accesses": 40, "market_share_pct": 20.0},
            {"company_name": "Empresa B", "accesses": 50, "market_share_pct": 25.0},
        ]
    )
    chart = prepare_provider_chart(source)

    assert chart["Prestadora"].tolist() == ["Empresa B", "Empresa A"]
    assert chart["Acessos formatados"].tolist() == ["50", "100"]
    assert chart["Participação"].tolist() == ["25,00%", "50,00%"]


def test_access_medium_chart_calculates_share() -> None:
    source = pd.DataFrame(
        [
            {"access_medium": "Fibra", "accesses": 80},
            {"access_medium": "Rádio", "accesses": 20},
        ]
    )
    chart = prepare_access_medium_chart(source)

    assert chart["Meio de acesso"].tolist() == ["Rádio", "Fibra"]
    assert chart["Participação"].tolist() == ["20,00%", "80,00%"]


def test_evolution_chart_localizes_months_and_values() -> None:
    source = pd.DataFrame(
        [
            {
                "date_key": 20260201,
                "reference_year": 2026,
                "reference_month": 2,
                "accesses": 56_000_000,
                "accesses_month_over_month_pct": 1.25,
            },
            {
                "date_key": 20260101,
                "reference_year": 2026,
                "reference_month": 1,
                "accesses": 55_000_000,
                "accesses_month_over_month_pct": float("nan"),
            },
        ]
    )
    chart = prepare_evolution_chart(source)

    assert chart["Competência"].tolist() == ["jan/26", "fev/26"]
    assert chart["Rótulo"].tolist() == ["55,00 mi", "56,00 mi"]
    assert chart["Variação mensal"].tolist() == ["Sem mês anterior", "1,25%"]
