"""Validated and deduplicated Silver processing for fixed broadband."""

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml


@dataclass(frozen=True)
class BroadbandSilverResult:
    """Reconciliation evidence for all monthly Silver partitions."""

    output_paths: list[Path]
    quarantine_paths: list[Path]
    records_input: int
    records_output: int
    records_rejected: int
    duplicate_rows_consolidated: int
    accesses_input: int
    accesses_output: int
    accesses_rejected: int
    created: bool


def load_silver_contract(path: Path) -> dict[str, Any]:
    contract = yaml.safe_load(path.read_text(encoding="utf-8"))
    if (
        contract.get("dataset") != "fixed_broadband_accesses"
        or contract.get("layer") != "silver"
        or not contract.get("grain")
        or not contract.get("rules")
    ):
        raise ValueError("Invalid fixed-broadband Silver contract")
    return contract


def validate_and_aggregate_broadband(
    bronze: pd.DataFrame,
    municipalities: pd.DataFrame,
    contract: dict[str, Any],
    silver_timestamp: datetime | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Validate rows, canonicalize geography, and consolidate the candidate grain."""
    required_dim = {"municipality_id", "ibge_code", "municipality_name", "state_code"}
    if missing := required_dim.difference(municipalities.columns):
        raise ValueError(f"Municipality dimension missing columns: {sorted(missing)}")
    timestamp = (silver_timestamp or datetime.now(UTC)).isoformat()
    dim = municipalities[list(required_dim)].drop_duplicates("ibge_code")
    typed = bronze.merge(dim, on="ibge_code", how="left", suffixes=("_source", ""))
    rules = contract["rules"]
    reasons: list[list[str]] = [[] for _ in range(len(typed))]

    def add(mask: pd.Series, reason: str) -> None:
        for position in mask.fillna(True).to_numpy().nonzero()[0]:
            reasons[position].append(reason)

    add(typed["reference_year"].lt(rules["minimum_year"]), "invalid_reference_year")
    add(
        ~typed["reference_month"].between(
            rules["minimum_month"], rules["maximum_month"], inclusive="both"
        ),
        "invalid_reference_month",
    )
    add(~typed["company_cnpj"].str.fullmatch(rules["cnpj_regex"]), "invalid_cnpj")
    add(typed["speed_mbps"].lt(rules["minimum_speed_mbps"]), "negative_speed")
    add(typed["accesses"].lt(rules["minimum_accesses"]), "invalid_accesses")
    add(~typed["provider_size"].isin(rules["accepted_provider_sizes"]), "invalid_provider_size")
    add(~typed["speed_range"].isin(rules["accepted_speed_ranges"]), "invalid_speed_range")
    speed = typed["speed_mbps"]
    speed_range_valid = (
        (typed["speed_range"].eq("0Kbps a 512Kbps") & speed.ge(0) & speed.lt(0.512))
        | (typed["speed_range"].eq("512kbps a 2Mbps") & speed.ge(0.512) & speed.le(2))
        | (typed["speed_range"].eq("2Mbps a 12Mbps") & speed.gt(2) & speed.le(12))
        | (typed["speed_range"].eq("12Mbps a 34Mbps") & speed.gt(12) & speed.le(34))
        | (typed["speed_range"].eq("> 34Mbps") & speed.gt(34))
    )
    add(~speed_range_valid, "speed_outside_range")
    add(~typed["person_type"].isin(rules["accepted_person_types"]), "invalid_person_type")
    add(~typed["product_type"].isin(rules["accepted_product_types"]), "invalid_product_type")
    add(~typed["access_medium"].isin(rules["accepted_access_media"]), "invalid_access_medium")
    add(typed["municipality_id"].isna(), "ibge_code_not_in_dimension")
    add(
        typed["state_code_source"].ne(typed["state_code"]) & typed["municipality_id"].notna(),
        "state_code_mismatch",
    )

    rejection_reason = pd.Series(("|".join(items) for items in reasons), dtype="string")
    rejected = typed.loc[rejection_reason.ne("")].copy()
    rejected["rejection_reason"] = rejection_reason[rejection_reason.ne("")].to_numpy()
    rejected["rejection_timestamp"] = timestamp
    valid = typed.loc[rejection_reason.eq("")].copy()

    grain = contract["grain"]
    lineage = [
        "_source_file",
        "_ingestion_timestamp",
        "_pipeline_run_id",
        "_sha256",
        "_reference_date",
        "_schema_version",
    ]
    aggregations: dict[str, str] = {
        "municipality_id": "first",
        "municipality_name": "first",
        "accesses": "sum",
        "municipality_name_source": "first",
    }
    aggregations.update(dict.fromkeys(lineage, "first"))
    silver = valid.groupby(grain, as_index=False, dropna=False, observed=True).agg(
        **{column: (column, operation) for column, operation in aggregations.items()},
        source_row_count=("accesses", "size"),
    )
    silver["_silver_timestamp"] = timestamp
    silver["_silver_schema_version"] = int(contract["version"])
    return silver, rejected.reset_index(drop=True)


def _write_once(frame: pd.DataFrame, path: Path, layer: str, source_hash: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return False
    temporary = path.parent / f".{path.name}.part"
    table = pa.Table.from_pandas(frame, preserve_index=False)
    metadata = {
        **(table.schema.metadata or {}),
        b"layer": layer.encode(),
        b"source_sha256": source_hash.encode(),
    }
    try:
        pq.write_table(table.replace_schema_metadata(metadata), temporary, compression="zstd")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return True


def build_broadband_silver(
    bronze_paths: list[Path],
    municipality_path: Path,
    contract_path: Path,
    silver_root: Path,
    quarantine_root: Path,
) -> BroadbandSilverResult:
    """Build immutable monthly Silver and quarantine artifacts with reconciliation totals."""
    if not bronze_paths:
        raise ValueError("No Broadband Bronze partitions supplied")
    contract = load_silver_contract(contract_path)
    municipalities = pd.read_parquet(municipality_path)
    output_paths: list[Path] = []
    quarantine_paths: list[Path] = []
    counts = {
        "input": 0,
        "output": 0,
        "rejected": 0,
        "access_in": 0,
        "access_out": 0,
        "access_rejected": 0,
    }
    created = False
    for bronze_path in sorted(bronze_paths):
        bronze = pd.read_parquet(bronze_path)
        source_hash = str(bronze["_sha256"].iloc[0])
        year = int(bronze["reference_year"].iloc[0])
        month = int(bronze["reference_month"].iloc[0])
        name = f"sha256={source_hash[:16]}.parquet"
        output = (
            silver_root
            / "dataset=fixed_broadband_accesses"
            / f"year={year}"
            / f"month={month:02d}"
            / name
        )
        quarantine = (
            quarantine_root / "invalid_broadband" / f"year={year}" / f"month={month:02d}" / name
        )
        if output.exists() and quarantine.exists():
            silver = pd.read_parquet(output, columns=["accesses", "source_row_count"])
            rejected = pd.read_parquet(quarantine, columns=["accesses"])
            input_rows = int(silver["source_row_count"].sum()) + len(rejected)
            access_input = int(silver["accesses"].sum()) + int(rejected["accesses"].sum())
        else:
            silver, rejected = validate_and_aggregate_broadband(bronze, municipalities, contract)
            input_rows = len(bronze)
            access_input = int(bronze["accesses"].sum())
            created |= _write_once(silver, output, "silver", source_hash)
            _write_once(rejected, quarantine, "quarantine", source_hash)
        output_paths.append(output)
        quarantine_paths.append(quarantine)
        counts["input"] += input_rows
        counts["output"] += len(silver)
        counts["rejected"] += len(rejected)
        counts["access_in"] += access_input
        counts["access_out"] += int(silver["accesses"].sum())
        counts["access_rejected"] += int(rejected["accesses"].sum())

    return BroadbandSilverResult(
        output_paths=output_paths,
        quarantine_paths=quarantine_paths,
        records_input=counts["input"],
        records_output=counts["output"],
        records_rejected=counts["rejected"],
        duplicate_rows_consolidated=counts["input"] - counts["rejected"] - counts["output"],
        accesses_input=counts["access_in"],
        accesses_output=counts["access_out"],
        accesses_rejected=counts["access_rejected"],
        created=created,
    )
