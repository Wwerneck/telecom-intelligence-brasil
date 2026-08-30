from pathlib import Path

import pandas as pd

from telecom_intelligence.analytics.broadband_marts import build_broadband_marts
from telecom_intelligence.ingestion.manifest import ManifestRecord
from telecom_intelligence.quality.broadband_profiling import EXPECTED_COLUMNS
from telecom_intelligence.transformation.broadband import build_broadband_bronze
from telecom_intelligence.transformation.broadband_silver import build_broadband_silver
from telecom_intelligence.transformation.fact_broadband import build_broadband_fact


def source_row(accesses: str) -> list[str]:
    return [
        "2026",
        "6",
        "OUTROS",
        "EMPRESA",
        "00123456000199",
        "Pequeno Porte",
        "GO",
        "Nome histórico",
        "5208707",
        "> 34Mbps",
        "100,0",
        "FTTH",
        "Fibra",
        "Pessoa Física",
        "INTERNET",
        accesses,
    ]


def test_raw_to_mart_reconciles_accesses(tmp_path: Path) -> None:
    raw = tmp_path / "raw.csv"
    pd.DataFrame([source_row("10"), source_row("15")], columns=EXPECTED_COLUMNS).to_csv(
        raw, sep=";", index=False
    )
    record = ManifestRecord(
        source="ANATEL",
        dataset="fixed_broadband_accesses",
        reference_date="2026",
        source_file=raw.name,
        raw_path=str(raw),
        download_timestamp="2026-08-29T00:00:00+00:00",
        file_size=raw.stat().st_size,
        sha256="a" * 64,
        status="downloaded",
        records_loaded=None,
        pipeline_run_id="integration-test",
    )
    project = Path()
    bronze = build_broadband_bronze(
        record,
        project / "config/schemas/fixed_broadband_accesses_bronze.yml",
        tmp_path / "bronze",
        chunk_size=1,
    )
    dimension = pd.DataFrame(
        [
            {
                "municipality_id": 5208707,
                "ibge_code": 5208707,
                "municipality_name": "Goiânia",
                "state_code": "GO",
                "state_name": "Goiás",
                "region_name": "Centro-Oeste",
                "population": 1_500_000,
                "population_reference_year": 2025,
            }
        ]
    )
    dimension_path = tmp_path / "dim_municipality.parquet"
    dimension.to_parquet(dimension_path, index=False)
    silver = build_broadband_silver(
        bronze.output_paths,
        dimension_path,
        project / "config/schemas/fixed_broadband_accesses_silver.yml",
        tmp_path / "silver",
        tmp_path / "quarantine",
    )
    fact = build_broadband_fact(silver.output_paths, dimension_path, tmp_path / "gold")
    marts = build_broadband_marts(fact.fact_paths, dimension_path, tmp_path / "marts")
    national = pd.read_parquet(marts.output_paths["mart_broadband_national_monthly"])

    assert bronze.records_output == 2
    assert silver.records_output == 1
    assert silver.duplicate_rows_consolidated == 1
    assert fact.accesses_output == 25
    assert national.loc[0, "accesses"] == 25
