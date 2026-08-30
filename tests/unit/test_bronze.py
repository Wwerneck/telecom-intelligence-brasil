import json
from datetime import UTC, datetime
from pathlib import Path

import pyarrow.parquet as pq

from telecom_intelligence.ingestion.manifest import ManifestRecord
from telecom_intelligence.transformation.bronze import (
    build_municipality_bronze,
    transform_municipality_to_bronze,
)


def contract() -> dict:
    return {
        "version": 1,
        "layer": "bronze",
        "columns": [
            {"name": "ibge_code", "type": "int64", "nullable": False, "source": "id"},
            {
                "name": "municipality_name",
                "type": "string",
                "nullable": False,
                "source": "nome",
            },
        ],
    }


def record(raw_path: Path) -> ManifestRecord:
    return ManifestRecord(
        source="IBGE",
        dataset="municipality_directory",
        reference_date="2026-08-28",
        source_file="municipios",
        raw_path=str(raw_path),
        download_timestamp="2026-08-28T21:05:33+00:00",
        file_size=1,
        sha256="a" * 64,
        status="downloaded",
        records_loaded=None,
        pipeline_run_id="run-1",
    )


def test_bronze_preserves_rows_and_adds_lineage(tmp_path: Path) -> None:
    raw_path = tmp_path / "municipios"
    raw_path.write_text(json.dumps([{"id": 5200050, "nome": "Abadia de Goiás"}]))

    frame = build_municipality_bronze(
        raw_path,
        record(raw_path),
        contract(),
        datetime(2026, 8, 28, tzinfo=UTC),
    )

    assert frame.loc[0, "municipality_name"] == "Abadia de Goiás"
    assert frame.loc[0, "_sha256"] == "a" * 64
    assert str(frame["ibge_code"].dtype) == "Int64"


def test_bronze_detects_missing_source_column(tmp_path: Path) -> None:
    raw_path = tmp_path / "municipios"
    raw_path.write_text(json.dumps([{"id": 5200050}]))

    try:
        build_municipality_bronze(raw_path, record(raw_path), contract())
    except ValueError as error:
        assert "Critical schema drift" in str(error)
    else:
        raise AssertionError("Expected schema drift failure")


def test_parquet_write_is_idempotent(tmp_path: Path) -> None:
    raw_path = tmp_path / "municipios"
    raw_path.write_text(json.dumps([{"id": 5200050, "nome": "Abadia de Goiás"}]))
    schema_path = tmp_path / "schema.yml"
    schema_path.write_text(
        """version: 1
layer: bronze
columns:
  - {name: ibge_code, type: int64, nullable: false, source: id}
  - {name: municipality_name, type: string, nullable: false, source: nome}
"""
    )

    first = transform_municipality_to_bronze(record(raw_path), schema_path, tmp_path / "bronze")
    second = transform_municipality_to_bronze(record(raw_path), schema_path, tmp_path / "bronze")

    assert first.created is True
    assert second.created is False
    assert pq.read_table(first.output_path).num_rows == 1
    assert pq.read_metadata(first.output_path).metadata[b"layer"] == b"bronze"
