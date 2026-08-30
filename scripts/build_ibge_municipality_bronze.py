"""Build the Bronze municipality Parquet from the latest successful RAW manifest row."""

import json
import sqlite3
from pathlib import Path

from telecom_intelligence.ingestion.manifest import ManifestRecord
from telecom_intelligence.transformation.bronze import transform_municipality_to_bronze


def latest_manifest_record(database_path: Path) -> ManifestRecord:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            """
            SELECT source, dataset, reference_date, source_file, raw_path,
                   download_timestamp, file_size, sha256, status,
                   records_loaded, pipeline_run_id
            FROM ingestion_manifest
            WHERE dataset = 'municipality_directory' AND status = 'downloaded'
            ORDER BY download_timestamp DESC
            LIMIT 1
            """
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        raise RuntimeError("No successful municipality RAW ingestion found")
    return ManifestRecord(**dict(row))


def main() -> None:
    result = transform_municipality_to_bronze(
        latest_manifest_record(Path("data/ingestion_manifest.db")),
        Path("config/schemas/municipality_directory_bronze.yml"),
        Path("data/bronze"),
    )
    print(
        json.dumps(
            {
                "output_path": str(result.output_path),
                "records_input": result.records_input,
                "records_output": result.records_output,
                "records_rejected": result.records_rejected,
                "created": result.created,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
