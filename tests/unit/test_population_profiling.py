import json
from pathlib import Path

import pandas as pd

from telecom_intelligence.quality.population_profiling import (
    load_sidra_response,
    profile_population,
)


def response() -> list[dict[str, str]]:
    return [
        {"D1C": "Município (Código)", "V": "Valor"},
        {
            "D1C": "5200050",
            "V": "1000",
            "MN": "Pessoas",
            "D2N": "População residente estimada",
            "D3N": "2025",
        },
    ]


def test_sidra_header_is_not_counted_as_data(tmp_path: Path) -> None:
    path = tmp_path / "sidra.json"
    path.write_text(json.dumps(response()), encoding="utf-8")

    header, frame = load_sidra_response(path)

    assert header["V"] == "Valor"
    assert len(frame) == 1


def test_population_profile_checks_referential_coverage(tmp_path: Path) -> None:
    path = tmp_path / "sidra.json"
    path.write_text(json.dumps(response()), encoding="utf-8")

    profile = profile_population(path, pd.Series([5200050, 5101837]))

    assert profile.rows == 1
    assert profile.non_numeric_values == 0
    assert profile.codes_not_in_geography == 0
    assert profile.geography_not_in_population == 1
