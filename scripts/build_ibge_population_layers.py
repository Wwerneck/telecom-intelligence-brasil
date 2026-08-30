"""Build Bronze and Silver population layers from the latest successful RAW ingestion."""

import json
import sqlite3
from pathlib import Path

from telecom_intelligence.ingestion.manifest import ManifestRecord
from telecom_intelligence.transformation.population import (
    build_population_bronze,
    build_population_silver,
)


def latest_population_manifest() -> ManifestRecord:
    connection = sqlite3.connect("data/ingestion_manifest.db")
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            """SELECT source, dataset, reference_date, source_file, raw_path,
                      download_timestamp, file_size, sha256, status,
                      records_loaded, pipeline_run_id
               FROM ingestion_manifest
               WHERE dataset = 'municipality_population' AND status = 'downloaded'
               ORDER BY download_timestamp DESC LIMIT 1"""
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        raise RuntimeError("No successful population ingestion found")
    return ManifestRecord(**dict(row))


def main() -> None:
    bronze = build_population_bronze(
        latest_population_manifest(),
        Path("config/schemas/municipality_population_bronze.yml"),
        Path("data/bronze"),
    )
    silver = build_population_silver(
        bronze.output_path,
        Path("config/schemas/municipality_population_silver.yml"),
        Path("data/silver"),
        Path("data/quarantine"),
    )
    print(json.dumps({"bronze": vars(bronze), "silver": vars(silver)}, default=str, indent=2))


if __name__ == "__main__":
    main()
