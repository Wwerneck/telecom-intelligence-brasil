"""Gold fact model for validated fixed-broadband accesses."""

import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


@dataclass(frozen=True)
class BroadbandFactResult:
    """Artifacts and reconciliation totals from a fact build."""

    fact_paths: list[Path]
    date_dimension_path: Path
    records_input: int
    records_output: int
    accesses_input: int
    accesses_output: int
    source_rows_represented: int
    created: bool


FACT_GRAIN = [
    "date_key",
    "municipality_id",
    "economic_group",
    "company_name",
    "company_cnpj",
    "provider_size",
    "speed_range",
    "speed_mbps",
    "technology",
    "access_medium",
    "person_type",
    "product_type",
]


def build_monthly_date_dimension(silver: pd.DataFrame) -> pd.DataFrame:
    """Create one date row for the first day of each evidenced reference month."""
    periods = silver[["reference_year", "reference_month"]].drop_duplicates()
    dates = pd.to_datetime(
        {"year": periods["reference_year"], "month": periods["reference_month"], "day": 1},
        errors="raise",
    ).sort_values()
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
    dimension = pd.DataFrame({"date": dates.dt.date})
    dimension["date_key"] = dates.dt.strftime("%Y%m%d").astype("int32").to_numpy()
    dimension["year"] = dates.dt.year.astype("int16").to_numpy()
    dimension["quarter"] = dates.dt.quarter.astype("int8").to_numpy()
    dimension["month"] = dates.dt.month.astype("int8").to_numpy()
    dimension["month_name"] = dimension["month"].map(lambda value: month_names[value - 1])
    dimension["year_month"] = dates.dt.strftime("%Y-%m").to_numpy()
    return dimension[
        ["date_key", "date", "year", "quarter", "month", "month_name", "year_month"]
    ].reset_index(drop=True)


def build_fact_frame(
    silver: pd.DataFrame, municipalities: pd.DataFrame, dates: pd.DataFrame
) -> pd.DataFrame:
    """Project the fact and enforce its dimensional and measure invariants."""
    required = set(FACT_GRAIN[2:]) | {
        "reference_year",
        "reference_month",
        "ibge_code",
        "municipality_id",
        "accesses",
        "source_row_count",
        "_source_file",
        "_pipeline_run_id",
        "_sha256",
        "_silver_schema_version",
    }
    if missing := required.difference(silver.columns):
        raise ValueError(f"Cannot build broadband fact; missing {sorted(missing)}")
    if silver.duplicated(["reference_year", "reference_month", "ibge_code", *FACT_GRAIN[2:]]).any():
        raise ValueError("Silver grain violation before fact build")
    if municipalities["municipality_id"].duplicated().any():
        raise ValueError("dim_municipality key is not unique")

    municipality_keys = municipalities[["municipality_id", "ibge_code"]]
    fact = silver.drop(columns="municipality_id").merge(
        municipality_keys, on="ibge_code", how="left", validate="many_to_one"
    )
    if fact["municipality_id"].isna().any():
        raise ValueError("Fact contains municipality foreign-key gaps")
    fact["date_key"] = (
        fact["reference_year"].astype("int32") * 10_000
        + fact["reference_month"].astype("int32") * 100
        + 1
    )
    if not fact["date_key"].isin(dates["date_key"]).all():
        raise ValueError("Fact contains date foreign-key gaps")

    columns = [
        *FACT_GRAIN,
        "ibge_code",
        "reference_year",
        "reference_month",
        "accesses",
        "source_row_count",
        "_source_file",
        "_pipeline_run_id",
        "_sha256",
        "_silver_schema_version",
    ]
    fact = fact[columns].copy()
    if fact.duplicated(FACT_GRAIN).any():
        raise ValueError("Fact grain violation after dimensional joins")
    if fact["accesses"].sum() != silver["accesses"].sum():
        raise ValueError("Access reconciliation failed during fact build")
    if fact["source_row_count"].sum() != silver["source_row_count"].sum():
        raise ValueError("Source-row reconciliation failed during fact build")
    return fact.sort_values(FACT_GRAIN).reset_index(drop=True)


def _write_once(frame: pd.DataFrame, path: Path, model: str, source_hash: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return False
    temporary = path.parent / f".{path.name}.part"
    table = pa.Table.from_pandas(frame, preserve_index=False)
    metadata = {
        **(table.schema.metadata or {}),
        b"layer": b"gold",
        b"model": model.encode(),
        b"source_sha256": source_hash.encode(),
    }
    try:
        pq.write_table(table.replace_schema_metadata(metadata), temporary, compression="zstd")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return True


def build_broadband_fact(
    silver_paths: list[Path], municipality_path: Path, gold_root: Path
) -> BroadbandFactResult:
    """Build monthly fact partitions and their evidenced date dimension."""
    if not silver_paths:
        raise ValueError("No Broadband Silver partitions supplied")
    municipalities = pd.read_parquet(municipality_path)
    period_frames = [
        pd.read_parquet(path, columns=["reference_year", "reference_month", "_sha256"])
        for path in sorted(silver_paths)
    ]
    periods = pd.concat(period_frames, ignore_index=True)
    dates = build_monthly_date_dimension(periods)
    source_hashes = sorted(periods["_sha256"].unique().tolist())
    if len(source_hashes) != 1:
        raise ValueError("Expected one source hash across Broadband Silver partitions")
    source_hash = source_hashes[0]

    date_path = (
        gold_root
        / "dim_date"
        / "source=fixed_broadband_accesses"
        / f"sha256={source_hash[:16]}.parquet"
    )
    created = _write_once(dates, date_path, "dim_date", source_hash)
    fact_paths: list[Path] = []
    records_input = records_output = accesses_input = accesses_output = source_rows = 0
    for silver_path in sorted(silver_paths):
        silver = pd.read_parquet(silver_path)
        fact = build_fact_frame(silver, municipalities, dates)
        years = fact["reference_year"].unique()
        months = fact["reference_month"].unique()
        if len(years) != 1 or len(months) != 1:
            raise ValueError(f"Silver partition mixes reference periods: {silver_path}")
        year, month = int(years[0]), int(months[0])
        path = (
            gold_root
            / "fact_broadband_accesses"
            / f"year={year}"
            / f"month={month:02d}"
            / f"sha256={source_hash[:16]}.parquet"
        )
        created |= _write_once(fact, path, "fact_broadband_accesses", source_hash)
        fact_paths.append(path)
        records_input += len(silver)
        records_output += len(fact)
        accesses_input += int(silver["accesses"].sum())
        accesses_output += int(fact["accesses"].sum())
        source_rows += int(fact["source_row_count"].sum())
    return BroadbandFactResult(
        fact_paths=fact_paths,
        date_dimension_path=date_path,
        records_input=records_input,
        records_output=records_output,
        accesses_input=accesses_input,
        accesses_output=accesses_output,
        source_rows_represented=source_rows,
        created=created,
    )
