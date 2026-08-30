"""Profiling for SIDRA municipal population responses."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class PopulationProfile:
    """Validated observations from one SIDRA population artifact."""

    rows: int
    unique_ibge_codes: int
    duplicate_codes: int
    invalid_codes: int
    non_numeric_values: int
    negative_values: int
    minimum_population: int
    maximum_population: int
    codes_not_in_geography: int
    geography_not_in_population: int
    unit_values: list[str]
    variable_values: list[str]
    period_values: list[str]


def load_sidra_response(path: Path) -> tuple[dict[str, Any], pd.DataFrame]:
    """Separate SIDRA's descriptive first row from actual observations."""
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, list) or len(document) < 2:
        raise ValueError("SIDRA response must contain a header and data rows")
    header, rows = document[0], document[1:]
    if header.get("D1C") != "Município (Código)" or header.get("V") != "Valor":
        raise ValueError("Unexpected SIDRA response header")
    return header, pd.DataFrame(rows)


def profile_population(raw_path: Path, geography_codes: pd.Series) -> PopulationProfile:
    """Profile numeric validity and referential coverage against official geography."""
    _, frame = load_sidra_response(raw_path)
    codes = pd.to_numeric(frame["D1C"], errors="coerce")
    values = pd.to_numeric(frame["V"], errors="coerce")
    valid_codes = set(codes.dropna().astype(int))
    official_codes = set(geography_codes.astype(int))
    return PopulationProfile(
        rows=len(frame),
        unique_ibge_codes=int(codes.nunique()),
        duplicate_codes=int(codes.duplicated(keep=False).sum()),
        invalid_codes=int(codes.isna().sum()),
        non_numeric_values=int(values.isna().sum()),
        negative_values=int(values.lt(0).sum()),
        minimum_population=int(values.min()),
        maximum_population=int(values.max()),
        codes_not_in_geography=len(valid_codes - official_codes),
        geography_not_in_population=len(official_codes - valid_codes),
        unit_values=sorted(frame["MN"].dropna().unique().tolist()),
        variable_values=sorted(frame["D2N"].dropna().unique().tolist()),
        period_values=sorted(frame["D3N"].dropna().unique().tolist()),
    )


def write_population_profile(
    raw_path: Path, geography_path: Path, output_path: Path
) -> PopulationProfile:
    """Profile and persist evidence as JSON."""
    geography = pd.read_parquet(geography_path)
    profile = profile_population(raw_path, geography["ibge_code"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(vars(profile), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return profile
