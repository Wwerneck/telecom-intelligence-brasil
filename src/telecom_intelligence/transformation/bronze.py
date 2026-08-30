"""Minimal, traceable RAW-to-Bronze transformations."""

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
from telecom_intelligence.quality.profiling import flatten_records, load_json_records


@dataclass(frozen=True)
class BronzeResult:
    """Auditable result of one RAW-to-Bronze execution."""

    output_path: Path
    records_input: int
    records_output: int
    records_rejected: int
    created: bool


def load_schema_contract(path: Path) -> dict[str, Any]:
    """Load a versioned Bronze schema contract."""
    contract = yaml.safe_load(path.read_text(encoding="utf-8"))
    if contract.get("layer") != "bronze" or not contract.get("columns"):
        raise ValueError("Invalid Bronze schema contract")
    return contract


def build_municipality_bronze(
    raw_path: Path,
    manifest_record: ManifestRecord,
    schema_contract: dict[str, Any],
    bronze_timestamp: datetime | None = None,
) -> pd.DataFrame:
    """Project official fields and attach lineage without cleansing source values."""
    source = flatten_records(load_json_records(raw_path))
    mappings = {column["source"]: column["name"] for column in schema_contract["columns"]}
    missing_source_columns = set(mappings).difference(source.columns)
    if missing_source_columns:
        raise ValueError(f"Critical schema drift: missing {sorted(missing_source_columns)}")

    bronze = source[list(mappings)].rename(columns=mappings).copy()
    for column in schema_contract["columns"]:
        name = column["name"]
        if column["type"] == "int64":
            bronze[name] = bronze[name].astype("Int64")
        elif column["type"] == "string":
            bronze[name] = bronze[name].astype("string")

    timestamp = bronze_timestamp or datetime.now(UTC)
    bronze["_source_file"] = manifest_record.source_file
    bronze["_ingestion_timestamp"] = manifest_record.download_timestamp
    bronze["_pipeline_run_id"] = manifest_record.pipeline_run_id
    bronze["_sha256"] = manifest_record.sha256
    bronze["_reference_date"] = manifest_record.reference_date
    bronze["_bronze_timestamp"] = timestamp.isoformat()
    bronze["_schema_version"] = int(schema_contract["version"])
    return bronze


def write_bronze_parquet(
    frame: pd.DataFrame,
    output_root: Path,
    manifest_record: ManifestRecord,
) -> tuple[Path, bool]:
    """Atomically persist a content-addressed Parquet artifact without overwriting it."""
    output_directory = (
        output_root
        / f"dataset={manifest_record.dataset}"
        / f"reference_date={manifest_record.reference_date}"
    )
    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / f"sha256={manifest_record.sha256[:16]}.parquet"
    if output_path.exists():
        return output_path, False

    temporary_path = output_directory / f".{manifest_record.pipeline_run_id}.parquet.part"
    table = pa.Table.from_pandas(frame, preserve_index=False)
    metadata = dict(table.schema.metadata or {})
    metadata.update(
        {
            b"layer": b"bronze",
            b"source_sha256": manifest_record.sha256.encode(),
            b"reference_date": manifest_record.reference_date.encode(),
        }
    )
    try:
        pq.write_table(table.replace_schema_metadata(metadata), temporary_path, compression="zstd")
        os.replace(temporary_path, output_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return output_path, True


def transform_municipality_to_bronze(
    manifest_record: ManifestRecord,
    schema_path: Path,
    output_root: Path,
) -> BronzeResult:
    """Execute the complete, minimal municipality Bronze transformation."""
    contract = load_schema_contract(schema_path)
    frame = build_municipality_bronze(Path(manifest_record.raw_path), manifest_record, contract)
    output_path, created = write_bronze_parquet(frame, output_root, manifest_record)
    return BronzeResult(
        output_path=output_path,
        records_input=len(frame),
        records_output=len(frame),
        records_rejected=0,
        created=created,
    )
