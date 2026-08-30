"""Dimensional models built only from validated Silver data."""

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from telecom_intelligence.transformation.population import combined_lineage_hash


@dataclass(frozen=True)
class DimensionalResult:
    """Artifacts and row counts from a dimensional build."""

    municipality_path: Path
    date_path: Path
    municipality_rows: int
    date_rows: int
    created: bool


def build_dim_municipality(
    silver: pd.DataFrame, population_silver: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Build one current row per official IBGE municipality."""
    required = {
        "ibge_code",
        "municipality_name",
        "municipality_key",
        "state_id",
        "state_code",
        "state_name",
        "region_id",
        "region_code",
        "region_name",
        "immediate_region_id",
        "immediate_region_name",
        "intermediate_region_id",
        "intermediate_region_name",
        "_reference_date",
        "_sha256",
    }
    missing = required.difference(silver.columns)
    if missing:
        raise ValueError(f"Cannot build dim_municipality; missing {sorted(missing)}")
    if silver["ibge_code"].duplicated().any():
        raise ValueError("dim_municipality grain violation: duplicate ibge_code")

    dimension = silver[
        [
            "ibge_code",
            "municipality_name",
            "municipality_key",
            "state_id",
            "state_code",
            "state_name",
            "region_id",
            "region_code",
            "region_name",
            "immediate_region_id",
            "immediate_region_name",
            "intermediate_region_id",
            "intermediate_region_name",
            "legacy_microregion_id",
            "legacy_microregion_name",
            "legacy_mesoregion_id",
            "legacy_mesoregion_name",
            "_reference_date",
            "_sha256",
        ]
    ].copy()
    # Natural-key-derived warehouse key is stable across rebuilds and independently verifiable.
    dimension.insert(0, "municipality_id", dimension["ibge_code"].astype("Int64"))
    dimension = dimension.rename(
        columns={"_reference_date": "source_reference_date", "_sha256": "source_sha256"}
    )
    if population_silver is None:
        dimension["population"] = pd.Series(pd.NA, index=dimension.index, dtype="Int64")
        dimension["population_reference_year"] = pd.Series(
            pd.NA, index=dimension.index, dtype="Int64"
        )
        dimension["population_source_sha256"] = pd.Series(
            pd.NA, index=dimension.index, dtype="string"
        )
    else:
        population_fields = {
            "ibge_code",
            "population",
            "population_reference_year",
            "_sha256",
        }
        missing_population = population_fields.difference(population_silver.columns)
        if missing_population:
            raise ValueError(f"Population Silver missing {sorted(missing_population)}")
        if population_silver.duplicated(subset=["ibge_code", "population_reference_year"]).any():
            raise ValueError("Population grain violation")
        years = population_silver["population_reference_year"].dropna().unique()
        if len(years) != 1:
            raise ValueError("Expected exactly one population reference year")
        population = population_silver[
            ["ibge_code", "population", "population_reference_year", "_sha256"]
        ].rename(columns={"_sha256": "population_source_sha256"})
        dimension = dimension.merge(population, on="ibge_code", how="left", validate="one_to_one")
        if dimension["population"].isna().any():
            missing_codes = dimension.loc[dimension["population"].isna(), "ibge_code"].tolist()
            raise ValueError(f"Population referential gap for IBGE codes: {missing_codes[:10]}")
    return dimension.sort_values("ibge_code").reset_index(drop=True)


def build_dim_date(reference_dates: pd.Series) -> pd.DataFrame:
    """Build date attributes only for dates evidenced by source data."""
    dates = pd.to_datetime(reference_dates, errors="raise").dt.date.drop_duplicates().sort_values()
    rows = []
    month_names = (
        "janeiro",
        "fevereiro",
        "março",
        "abril",
        "maio",
        "junho",
        "julho",
        "agosto",
        "setembro",
        "outubro",
        "novembro",
        "dezembro",
    )
    for value in dates:
        assert isinstance(value, date)
        rows.append(
            {
                "date_key": int(value.strftime("%Y%m%d")),
                "date": value,
                "year": value.year,
                "quarter": (value.month - 1) // 3 + 1,
                "month": value.month,
                "month_name": month_names[value.month - 1],
                "year_month": value.strftime("%Y-%m"),
            }
        )
    return pd.DataFrame(rows)


def _write_once(frame: pd.DataFrame, target: Path, model: str) -> bool:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return False
    temporary = target.parent / f".{target.name}.part"
    table = pa.Table.from_pandas(frame, preserve_index=False)
    metadata = {**(table.schema.metadata or {}), b"layer": b"gold", b"model": model.encode()}
    try:
        pq.write_table(table.replace_schema_metadata(metadata), temporary, compression="zstd")
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return True


def build_dimensions(
    silver_path: Path, gold_root: Path, population_silver_path: Path | None = None
) -> DimensionalResult:
    """Build currently supported Gold dimensions from municipality Silver."""
    silver = pd.read_parquet(silver_path)
    population_silver = (
        pd.read_parquet(population_silver_path) if population_silver_path is not None else None
    )
    municipality = build_dim_municipality(silver, population_silver)
    date_dimension = build_dim_date(silver["_reference_date"])
    sha256 = str(silver["_sha256"].iloc[0])
    model_hash = (
        combined_lineage_hash(sha256, str(population_silver["_sha256"].iloc[0]))
        if population_silver is not None
        else sha256
    )
    municipality_path = gold_root / "dim_municipality" / f"sha256={model_hash[:16]}.parquet"
    date_path = gold_root / "dim_date" / f"sha256={sha256[:16]}.parquet"
    municipality_created = _write_once(municipality, municipality_path, "dim_municipality")
    date_created = _write_once(date_dimension, date_path, "dim_date")
    return DimensionalResult(
        municipality_path=municipality_path,
        date_path=date_path,
        municipality_rows=len(municipality),
        date_rows=len(date_dimension),
        created=municipality_created or date_created,
    )
