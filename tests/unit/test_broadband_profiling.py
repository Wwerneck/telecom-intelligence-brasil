from pathlib import Path

import pytest

from telecom_intelligence.quality.broadband_profiling import (
    EXPECTED_COLUMNS,
    profile_broadband_csv,
    write_broadband_profile,
)


def write_csv(path: Path, rows: list[list[str]]) -> None:
    lines = [";".join(EXPECTED_COLUMNS), *(";".join(row) for row in rows)]
    path.write_text("\n".join(lines), encoding="utf-8")


def valid_row() -> list[str]:
    return [
        "2026",
        "6",
        "OUTROS",
        "EMPRESA",
        "12345678000199",
        "Pequeno Porte",
        "GO",
        "Goiânia",
        "5208707",
        "> 34Mbps",
        "100,5",
        "FIBRA",
        "Fibra",
        "Pessoa Física",
        "INTERNET",
        "10",
    ]


def test_profiles_chunks_decimal_comma_and_cross_chunk_duplicates(tmp_path: Path) -> None:
    path = tmp_path / "broadband.csv"
    write_csv(path, [valid_row(), valid_row()])

    profile = profile_broadband_csv(path, chunk_size=1)

    assert profile.rows == 2
    assert profile.chunks == 2
    assert profile.reference_periods == ["2026-06"]
    assert profile.total_accesses == 20
    assert profile.non_numeric_speeds == 0
    assert profile.duplicate_grain_rows == 1


def test_reports_invalid_business_values_and_writes_json(tmp_path: Path) -> None:
    row = valid_row()
    row[1], row[6], row[8], row[10], row[15] = "13", "XX", "invalid", "n/a", "-2"
    path = tmp_path / "broadband.csv"
    write_csv(path, [row])

    profile = write_broadband_profile(path, tmp_path / "profile.json")

    assert profile.invalid_months == 1
    assert profile.invalid_ibge_codes == 1
    assert profile.invalid_ufs == 1
    assert profile.non_numeric_speeds == 1
    assert profile.negative_accesses == 1
    assert (tmp_path / "profile.json").exists()


def test_rejects_schema_drift(tmp_path: Path) -> None:
    path = tmp_path / "broadband.csv"
    path.write_text("wrong;columns\n1;2", encoding="utf-8")

    with pytest.raises(ValueError, match="Unexpected ANATEL columns"):
        profile_broadband_csv(path)
