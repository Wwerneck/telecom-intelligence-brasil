from pathlib import Path

import pandas as pd

from telecom_intelligence.analytics.dashboard_data import (
    available_periods,
    filter_period,
    format_decimal,
    format_integer,
    load_local_marts,
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
