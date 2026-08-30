"""Incremental RAW-to-Bronze processing for ANATEL fixed broadband."""

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


@dataclass(frozen=True)
class BroadbandBronzeResult:
    """Auditable result for a partitioned Broadband Bronze build."""

    output_paths: list[Path]
    records_input: int
    records_output: int
    records_rejected: int
    created: bool


def load_broadband_contract(path: Path) -> dict[str, Any]:
    """Load and minimally validate the versioned contract."""
    contract = yaml.safe_load(path.read_text(encoding="utf-8"))
    if (
        contract.get("dataset") != "fixed_broadband_accesses"
        or contract.get("layer") != "bronze"
        or not contract.get("columns")
    ):
        raise ValueError("Invalid fixed-broadband Bronze contract")
    return contract


def transform_broadband_chunk(
    source: pd.DataFrame,
    manifest_record: ManifestRecord,
    contract: dict[str, Any],
    bronze_timestamp: datetime,
) -> pd.DataFrame:
    """Project, type, and attach lineage while preserving every source row."""
    mappings = {column["source"]: column["name"] for column in contract["columns"]}
    missing = set(mappings).difference(source.columns)
    if missing:
        raise ValueError(f"Critical ANATEL schema drift: missing {sorted(missing)}")
    if source.columns.tolist() != list(mappings):
        unexpected = set(source.columns).difference(mappings)
        raise ValueError(f"Critical ANATEL schema drift: unexpected {sorted(unexpected)}")

    bronze = source.rename(columns=mappings).copy()
    for definition in contract["columns"]:
        name = definition["name"]
        data_type = definition["type"]
        if definition.get("decimal") == "comma":
            bronze[name] = bronze[name].str.replace(",", ".", regex=False)
        if data_type.startswith("int"):
            bronze[name] = pd.to_numeric(bronze[name], errors="raise").astype(data_type)
        elif data_type == "float64":
            bronze[name] = pd.to_numeric(bronze[name], errors="raise").astype("float64")
        elif data_type == "string":
            bronze[name] = bronze[name].astype("string")

    bronze["_source_file"] = manifest_record.source_file
    bronze["_ingestion_timestamp"] = manifest_record.download_timestamp
    bronze["_pipeline_run_id"] = manifest_record.pipeline_run_id
    bronze["_sha256"] = manifest_record.sha256
    bronze["_reference_date"] = manifest_record.reference_date
    bronze["_bronze_timestamp"] = bronze_timestamp.isoformat()
    bronze["_schema_version"] = int(contract["version"])
    return bronze


def _existing_outputs(output_root: Path, source_hash: str) -> list[Path]:
    return sorted(
        output_root.glob(
            f"dataset=fixed_broadband_accesses/year=*/month=*/sha256={source_hash[:16]}.parquet"
        )
    )


def build_broadband_bronze(
    manifest_record: ManifestRecord,
    contract_path: Path,
    output_root: Path,
    chunk_size: int = 100_000,
    bronze_timestamp: datetime | None = None,
) -> BroadbandBronzeResult:
    """Stream the CSV into immutable monthly Parquet partitions."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    existing = _existing_outputs(output_root, manifest_record.sha256)
    if existing:
        rows = sum(pq.read_metadata(path).num_rows for path in existing)
        return BroadbandBronzeResult(existing, rows, rows, 0, False)

    contract = load_broadband_contract(contract_path)
    timestamp = bronze_timestamp or datetime.now(UTC)
    writers: dict[tuple[int, int], pq.ParquetWriter] = {}
    temporary_paths: dict[tuple[int, int], Path] = {}
    final_paths: dict[tuple[int, int], Path] = {}
    records = 0
    try:
        chunks = pd.read_csv(
            manifest_record.raw_path,
            sep=";",
            encoding="utf-8-sig",
            dtype="string",
            chunksize=chunk_size,
            keep_default_na=True,
            low_memory=False,
        )
        for source in chunks:
            bronze = transform_broadband_chunk(source, manifest_record, contract, timestamp)
            records += len(bronze)
            for (year, month), partition in bronze.groupby(
                ["reference_year", "reference_month"], sort=True
            ):
                key = (int(year), int(month))
                if key not in writers:
                    directory = (
                        output_root
                        / "dataset=fixed_broadband_accesses"
                        / f"year={key[0]}"
                        / f"month={key[1]:02d}"
                    )
                    directory.mkdir(parents=True, exist_ok=True)
                    final = directory / f"sha256={manifest_record.sha256[:16]}.parquet"
                    temporary = directory / f".{manifest_record.pipeline_run_id}.parquet.part"
                    table = pa.Table.from_pandas(partition, preserve_index=False)
                    metadata = {
                        **(table.schema.metadata or {}),
                        b"layer": b"bronze",
                        b"source_sha256": manifest_record.sha256.encode(),
                        b"schema_version": str(contract["version"]).encode(),
                    }
                    table = table.replace_schema_metadata(metadata)
                    writers[key] = pq.ParquetWriter(temporary, table.schema, compression="zstd")
                    temporary_paths[key] = temporary
                    final_paths[key] = final
                else:
                    table = pa.Table.from_pandas(partition, preserve_index=False).cast(
                        writers[key].schema
                    )
                writers[key].write_table(table)
        for writer in writers.values():
            writer.close()
        writers.clear()
        for key, temporary in temporary_paths.items():
            os.replace(temporary, final_paths[key])
    finally:
        for writer in writers.values():
            writer.close()
        for temporary in temporary_paths.values():
            temporary.unlink(missing_ok=True)

    outputs = [final_paths[key] for key in sorted(final_paths)]
    return BroadbandBronzeResult(outputs, records, records, 0, True)
