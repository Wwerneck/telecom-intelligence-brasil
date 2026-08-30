"""Reference implementation of audited fixed-broadband analytical marts."""

import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


@dataclass(frozen=True)
class BroadbandMartsResult:
    """Paths and reconciliation totals for one marts build."""

    output_paths: dict[str, Path]
    fact_rows: int
    fact_accesses: int
    national_accesses: int
    created: bool


def build_month_marts(fact: pd.DataFrame, municipalities: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Aggregate one monthly fact partition without multiplying population."""
    periods = fact[["date_key", "reference_year", "reference_month"]].drop_duplicates()
    if len(periods) != 1:
        raise ValueError("Expected exactly one reference month per fact partition")
    if fact.duplicated(
        [
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
    ).any():
        raise ValueError("Fact grain violation")
    dim = municipalities[
        [
            "municipality_id",
            "ibge_code",
            "municipality_name",
            "state_code",
            "state_name",
            "region_name",
            "population",
            "population_reference_year",
        ]
    ].copy()
    if dim["municipality_id"].duplicated().any() or dim["population"].isna().any():
        raise ValueError("Invalid municipality dimension for penetration KPIs")

    group = ["date_key", "reference_year", "reference_month", "municipality_id"]
    municipality = fact.groupby(group, as_index=False, observed=True).agg(
        accesses=("accesses", "sum"),
        companies=("company_cnpj", "nunique"),
        source_row_count=("source_row_count", "sum"),
    )
    fiber = (
        fact.loc[fact["access_medium"].eq("Fibra")]
        .groupby(group, as_index=False, observed=True)["accesses"]
        .sum()
        .rename(columns={"accesses": "fiber_accesses"})
    )
    municipality = municipality.merge(fiber, on=group, how="left", validate="one_to_one")
    municipality["fiber_accesses"] = municipality["fiber_accesses"].fillna(0).astype("int64")
    municipality = municipality.merge(dim, on="municipality_id", how="left", validate="many_to_one")
    if municipality["population"].isna().any():
        raise ValueError("Municipality mart has population foreign-key gaps")
    municipality["accesses_per_100_inhabitants"] = (
        municipality["accesses"] / municipality["population"] * 100
    )
    municipality["fiber_share_pct"] = (
        municipality["fiber_accesses"] / municipality["accesses"] * 100
    )

    total_population = int(dim["population"].sum())
    period = periods.iloc[0]
    total_accesses = int(fact["accesses"].sum())
    fiber_accesses = int(fact.loc[fact["access_medium"].eq("Fibra"), "accesses"].sum())
    high_speed_accesses = int(fact.loc[fact["speed_range"].eq("> 34Mbps"), "accesses"].sum())
    national = pd.DataFrame(
        [
            {
                **period.to_dict(),
                "accesses": total_accesses,
                "fiber_accesses": fiber_accesses,
                "high_speed_accesses": high_speed_accesses,
                "municipalities_with_access": int(fact["municipality_id"].nunique()),
                "companies": int(fact["company_cnpj"].nunique()),
                "population": total_population,
                "population_reference_year": int(dim["population_reference_year"].iloc[0]),
                "accesses_per_100_inhabitants": total_accesses / total_population * 100,
                "fiber_share_pct": fiber_accesses / total_accesses * 100,
                "high_speed_share_pct": high_speed_accesses / total_accesses * 100,
            }
        ]
    )

    def share_mart(columns: list[str], name: str) -> pd.DataFrame:
        result = fact.groupby(
            ["date_key", "reference_year", "reference_month", *columns],
            as_index=False,
            observed=True,
        ).agg(accesses=("accesses", "sum"), municipalities=("municipality_id", "nunique"))
        result[f"{name}_share_pct"] = result["accesses"] / total_accesses * 100
        return result

    return {
        "mart_broadband_municipality_monthly": municipality,
        "mart_broadband_national_monthly": national,
        "mart_broadband_provider_monthly": share_mart(
            ["economic_group", "company_name", "company_cnpj", "provider_size"], "market"
        ),
        "mart_broadband_technology_monthly": share_mart(
            ["technology", "access_medium"], "technology"
        ),
        "mart_broadband_speed_monthly": share_mart(["speed_range"], "speed_range"),
    }


def _write_once(frame: pd.DataFrame, path: Path, model: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return False
    temporary = path.parent / f".{path.name}.part"
    table = pa.Table.from_pandas(frame, preserve_index=False)
    metadata = {**(table.schema.metadata or {}), b"layer": b"mart", b"model": model.encode()}
    try:
        pq.write_table(table.replace_schema_metadata(metadata), temporary, compression="zstd")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return True


def build_broadband_marts(
    fact_paths: list[Path], municipality_path: Path, output_root: Path
) -> BroadbandMartsResult:
    """Build all reference marts partition by partition and reconcile their totals."""
    if not fact_paths:
        raise ValueError("No broadband fact partitions supplied")
    municipalities = pd.read_parquet(municipality_path)
    accumulated: dict[str, list[pd.DataFrame]] = {}
    fact_rows = fact_accesses = 0
    source_hash: str | None = None
    for path in sorted(fact_paths):
        fact = pd.read_parquet(path)
        hashes = fact["_sha256"].unique().tolist()
        if len(hashes) != 1 or (source_hash is not None and hashes[0] != source_hash):
            raise ValueError("Inconsistent fact lineage hashes")
        source_hash = hashes[0]
        fact_rows += len(fact)
        fact_accesses += int(fact["accesses"].sum())
        for name, frame in build_month_marts(fact, municipalities).items():
            accumulated.setdefault(name, []).append(frame)

    assert source_hash is not None
    output_paths: dict[str, Path] = {}
    created = False
    national_accesses = 0
    for name, frames in accumulated.items():
        mart = pd.concat(frames, ignore_index=True)
        if name == "mart_broadband_national_monthly":
            mart = mart.sort_values("date_key").reset_index(drop=True)
            mart["accesses_month_over_month_pct"] = mart["accesses"].pct_change() * 100
        path = output_root / name / f"sha256={source_hash[:16]}.parquet"
        created |= _write_once(mart, path, name)
        output_paths[name] = path
        if name == "mart_broadband_national_monthly":
            national_accesses = int(mart["accesses"].sum())
    if fact_accesses != national_accesses:
        raise ValueError("National mart does not reconcile with fact accesses")
    return BroadbandMartsResult(output_paths, fact_rows, fact_accesses, national_accesses, created)
