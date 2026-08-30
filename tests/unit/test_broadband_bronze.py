from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import yaml

from telecom_intelligence.ingestion.manifest import ManifestRecord
from telecom_intelligence.quality.broadband_profiling import EXPECTED_COLUMNS
from telecom_intelligence.transformation.broadband import (
    build_broadband_bronze,
    transform_broadband_chunk,
)


def record(path: Path) -> ManifestRecord:
    return ManifestRecord(
        source="ANATEL",
        dataset="fixed_broadband_accesses",
        reference_date="2026",
        source_file=path.name,
        raw_path=str(path),
        download_timestamp="2026-08-28T22:00:00+00:00",
        file_size=1,
        sha256="b" * 64,
        status="downloaded",
        records_loaded=None,
        pipeline_run_id="run-1",
    )


def source_frame(month: str = "6") -> pd.DataFrame:
    values = [
        "2026",
        month,
        "OUTROS",
        "EMPRESA",
        "00123456000199",
        "Pequeno Porte",
        "GO",
        "Goiânia",
        "5208707",
        "> 34Mbps",
        "100,5",
        "FIBRA",
        "Fibra",
        "Pessoa Física",
        "INTERNET",
        "10",
    ]
    return pd.DataFrame([values], columns=EXPECTED_COLUMNS, dtype="string")


def contract() -> dict:
    return {
        "version": 1,
        "columns": [
            {"source": source, "name": name, "type": data_type, **extra}
            for source, name, data_type, extra in [
                ("Ano", "reference_year", "int16", {}),
                ("Mês", "reference_month", "int8", {}),
                ("Grupo Econômico", "economic_group", "string", {}),
                ("Empresa", "company_name", "string", {}),
                ("CNPJ", "company_cnpj", "string", {}),
                ("Porte da Prestadora", "provider_size", "string", {}),
                ("UF", "state_code", "string", {}),
                ("Município", "municipality_name", "string", {}),
                ("Código IBGE Município", "ibge_code", "int32", {}),
                ("Faixa de Velocidade", "speed_range", "string", {}),
                ("Velocidade", "speed_mbps", "float64", {"decimal": "comma"}),
                ("Tecnologia", "technology", "string", {}),
                ("Meio de Acesso", "access_medium", "string", {}),
                ("Tipo de Pessoa", "person_type", "string", {}),
                ("Tipo de Produto", "product_type", "string", {}),
                ("Acessos", "accesses", "int64", {}),
            ]
        ],
    }


def test_chunk_types_values_and_lineage() -> None:
    frame = transform_broadband_chunk(
        source_frame(), record(Path("raw.csv")), contract(), datetime(2026, 8, 29, tzinfo=UTC)
    )

    assert frame.loc[0, "company_cnpj"] == "00123456000199"
    assert frame.loc[0, "speed_mbps"] == 100.5
    assert frame.loc[0, "accesses"] == 10
    assert frame.loc[0, "_schema_version"] == 1


def test_partitioned_write_preserves_rows_and_is_idempotent(tmp_path: Path) -> None:
    raw = tmp_path / "raw.csv"
    pd.concat([source_frame("5"), source_frame("5"), source_frame("6")]).to_csv(
        raw, sep=";", index=False
    )
    schema = tmp_path / "schema.yml"
    schema.write_text(
        yaml.safe_dump({"dataset": "fixed_broadband_accesses", "layer": "bronze", **contract()}),
        encoding="utf-8",
    )

    first = build_broadband_bronze(record(raw), schema, tmp_path / "bronze", chunk_size=1)
    second = build_broadband_bronze(record(raw), schema, tmp_path / "bronze", chunk_size=1)

    assert first.created is True
    assert second.created is False
    assert len(first.output_paths) == 2
    assert sum(pq.read_metadata(path).num_rows for path in first.output_paths) == 3
    assert "month=05" in str(first.output_paths[0])
    assert pq.read_metadata(first.output_paths[0]).metadata[b"layer"] == b"bronze"
