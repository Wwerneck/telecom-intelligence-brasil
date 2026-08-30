"""Bronze and Silver processing for official SIDRA population estimates."""

import hashlib
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from telecom_intelligence.ingestion.manifest import ManifestRecord
from telecom_intelligence.quality.population_profiling import load_sidra_response


@dataclass(frozen=True)
class PopulationLayerResult:
    """Counts and paths for a population layer build."""

    output_path: Path
    quarantine_path: Path | None
    records_input: int
    records_output: int
    records_rejected: int
    created: bool


def load_contract(path: Path, expected_layer: str) -> dict[str, Any]:
    contract = yaml.safe_load(path.read_text(encoding="utf-8"))
    if contract.get("layer") != expected_layer:
        raise ValueError(f"Expected {expected_layer} contract")
    return contract


def build_population_bronze_frame(
    raw_path: Path,
    manifest_record: ManifestRecord,
    contract: dict[str, Any],
    bronze_timestamp: datetime | None = None,
) -> pd.DataFrame:
    """Remove SIDRA's descriptive header and project source fields without cleansing values."""
    _, source = load_sidra_response(raw_path)
    required = {"NC", "NN", "MC", "MN", "V", "D1C", "D1N", "D2C", "D2N", "D3C", "D3N"}
    missing = required.difference(source.columns)
    if missing:
        raise ValueError(f"Critical SIDRA schema drift: missing {sorted(missing)}")
    bronze = source.rename(
        columns={
            "NC": "territorial_level_code",
            "NN": "territorial_level_name",
            "MC": "unit_code",
            "MN": "unit_name",
            "V": "population_raw",
            "D1C": "ibge_code_raw",
            "D1N": "municipality_name_raw",
            "D2C": "variable_code",
            "D2N": "variable_name",
            "D3C": "period_code",
            "D3N": "period_name",
        }
    ).copy()
    for column in bronze.columns:
        bronze[column] = bronze[column].astype("string")
    bronze["_source_file"] = manifest_record.source_file
    bronze["_ingestion_timestamp"] = manifest_record.download_timestamp
    bronze["_pipeline_run_id"] = manifest_record.pipeline_run_id
    bronze["_sha256"] = manifest_record.sha256
    bronze["_reference_date"] = manifest_record.reference_date
    bronze["_bronze_timestamp"] = (bronze_timestamp or datetime.now(UTC)).isoformat()
    bronze["_schema_version"] = int(contract["version"])
    return bronze


def validate_population_silver(
    bronze: pd.DataFrame,
    contract: dict[str, Any],
    rejection_timestamp: datetime | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Type population fields and quarantine rows violating explicit domain rules."""
    typed = bronze.copy()
    typed["ibge_code"] = pd.to_numeric(typed["ibge_code_raw"], errors="coerce").astype("Int64")
    typed["population"] = pd.to_numeric(typed["population_raw"], errors="coerce").astype("Int64")
    typed["population_reference_year"] = pd.to_numeric(
        typed["period_code"], errors="coerce"
    ).astype("Int64")
    reasons: list[list[str]] = [[] for _ in range(len(typed))]

    def add(mask: pd.Series, reason: str) -> None:
        for position in mask.fillna(True).to_numpy().nonzero()[0]:
            reasons[position].append(reason)

    rules = contract["rules"]
    add(~typed["ibge_code_raw"].str.fullmatch(rules["ibge_code_regex"]), "invalid_ibge_code")
    add(typed["population"].isna(), "invalid_numeric")
    add(typed["population"].lt(rules["minimum_population"]), "negative_population")
    add(typed["unit_name"].ne(rules["accepted_unit"]), "invalid_unit")
    add(typed["variable_code"].ne(rules["accepted_variable_code"]), "invalid_variable")
    add(
        typed["population_reference_year"].ne(rules["accepted_year"]),
        "invalid_reference_year",
    )
    key = contract["primary_key"]
    add(typed.duplicated(subset=key, keep=False), "duplicate_key")
    rejection_reason = pd.Series(("|".join(item) for item in reasons), dtype="string")
    rejected = typed.loc[rejection_reason.ne("")].copy()
    rejected["rejection_reason"] = rejection_reason[rejection_reason.ne("")].to_numpy()
    rejected["source"] = rejected["_source_file"]
    rejected["pipeline_run"] = rejected["_pipeline_run_id"]
    rejected["rejection_timestamp"] = (rejection_timestamp or datetime.now(UTC)).isoformat()
    valid = typed.loc[rejection_reason.eq("")].copy()
    valid["_silver_timestamp"] = (rejection_timestamp or datetime.now(UTC)).isoformat()
    valid["_silver_schema_version"] = int(contract["version"])
    return valid.reset_index(drop=True), rejected.reset_index(drop=True)


def _write_once(frame: pd.DataFrame, path: Path, layer: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return False
    temporary = path.parent / f".{path.name}.part"
    table = pa.Table.from_pandas(frame, preserve_index=False)
    metadata = {**(table.schema.metadata or {}), b"layer": layer.encode()}
    try:
        pq.write_table(table.replace_schema_metadata(metadata), temporary, compression="zstd")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return True


def build_population_bronze(
    manifest_record: ManifestRecord, contract_path: Path, output_root: Path
) -> PopulationLayerResult:
    contract = load_contract(contract_path, "bronze")
    frame = build_population_bronze_frame(Path(manifest_record.raw_path), manifest_record, contract)
    path = (
        output_root
        / "dataset=municipality_population"
        / f"reference_date={manifest_record.reference_date}"
        / f"sha256={manifest_record.sha256[:16]}.parquet"
    )
    created = _write_once(frame, path, "bronze")
    return PopulationLayerResult(path, None, len(frame), len(frame), 0, created)


def build_population_silver(
    bronze_path: Path, contract_path: Path, silver_root: Path, quarantine_root: Path
) -> PopulationLayerResult:
    contract = load_contract(contract_path, "silver")
    bronze = pd.read_parquet(bronze_path)
    valid, rejected = validate_population_silver(bronze, contract)
    sha256 = str(bronze["_sha256"].iloc[0])
    reference = str(bronze["_reference_date"].iloc[0])
    name = f"sha256={sha256[:16]}.parquet"
    output = silver_root / "dataset=municipality_population" / f"reference_date={reference}" / name
    quarantine = (
        quarantine_root
        / "invalid_population"
        / "dataset=municipality_population"
        / f"reference_date={reference}"
        / name
    )
    created = _write_once(valid, output, "silver")
    _write_once(rejected, quarantine, "quarantine")
    return PopulationLayerResult(
        output, quarantine, len(bronze), len(valid), len(rejected), created
    )


def combined_lineage_hash(geography_hash: str, population_hash: str) -> str:
    """Create a deterministic identity for a Gold model with two upstream artifacts."""
    return hashlib.sha256(f"{geography_hash}:{population_hash}".encode()).hexdigest()
