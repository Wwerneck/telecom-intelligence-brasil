"""Build monthly Bronze Parquet partitions from the latest ANATEL RAW ingestion."""

import argparse
import json
import sqlite3
from pathlib import Path

from telecom_intelligence.ingestion.manifest import ManifestRecord
from telecom_intelligence.transformation.broadband import build_broadband_bronze


def latest_manifest_record(database_path: Path) -> ManifestRecord:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            """SELECT source, dataset, reference_date, source_file, raw_path,
                      download_timestamp, file_size, sha256, status,
                      records_loaded, pipeline_run_id
               FROM ingestion_manifest
               WHERE dataset = 'fixed_broadband_accesses' AND status = 'downloaded'
               ORDER BY download_timestamp DESC LIMIT 1"""
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        raise RuntimeError("No successful fixed-broadband ingestion found")
    return ManifestRecord(**dict(row))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk-size", type=int, default=100_000)
    args = parser.parse_args()
    result = build_broadband_bronze(
        latest_manifest_record(Path("data/ingestion_manifest.db")),
        Path("config/schemas/fixed_broadband_accesses_bronze.yml"),
        Path("data/bronze"),
        args.chunk_size,
    )
    print(json.dumps(vars(result), default=str, indent=2))


if __name__ == "__main__":
    main()
