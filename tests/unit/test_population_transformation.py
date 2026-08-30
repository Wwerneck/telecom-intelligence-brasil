import json
from pathlib import Path

import pandas as pd

from telecom_intelligence.ingestion.manifest import ManifestRecord
from telecom_intelligence.transformation.population import (
    build_population_bronze_frame,
    combined_lineage_hash,
    validate_population_silver,
)


def manifest(path: Path) -> ManifestRecord:
    return ManifestRecord(
        "IBGE",
        "municipality_population",
        "2025",
        "2025",
        str(path),
        "2026-08-28T00:00:00+00:00",
        1,
        "a" * 64,
        "downloaded",
        None,
        "run-1",
    )


def bronze_contract() -> dict:
    return {"version": 1, "layer": "bronze"}


def silver_contract() -> dict:
    return {
        "version": 1,
        "primary_key": ["ibge_code", "population_reference_year"],
        "rules": {
            "ibge_code_regex": r"^[0-9]{7}$",
            "minimum_population": 0,
            "accepted_unit": "Pessoas",
            "accepted_variable_code": "9324",
            "accepted_year": 2025,
        },
    }


def test_population_header_is_removed_and_values_preserved(tmp_path: Path) -> None:
    raw = tmp_path / "population.json"
    raw.write_text(
        json.dumps(
            [
                {"D1C": "Município (Código)", "V": "Valor"},
                {
                    "NC": "6",
                    "NN": "Município",
                    "MC": "45",
                    "MN": "Pessoas",
                    "V": "1000",
                    "D1C": "5200050",
                    "D1N": "Abadia - GO",
                    "D2C": "9324",
                    "D2N": "População residente estimada",
                    "D3C": "2025",
                    "D3N": "2025",
                },
            ]
        ),
        encoding="utf-8",
    )
    frame = build_population_bronze_frame(raw, manifest(raw), bronze_contract())

    assert len(frame) == 1
    assert frame.loc[0, "population_raw"] == "1000"


def test_invalid_population_is_quarantined() -> None:
    frame = pd.DataFrame(
        [
            {
                "ibge_code_raw": "5200050",
                "population_raw": "-1",
                "period_code": "2025",
                "unit_name": "Pessoas",
                "variable_code": "9324",
                "_source_file": "2025",
                "_pipeline_run_id": "run-1",
            }
        ]
    )
    valid, rejected = validate_population_silver(frame, silver_contract())

    assert valid.empty
    assert rejected.loc[0, "rejection_reason"] == "negative_population"


def test_combined_lineage_hash_is_stable_and_order_sensitive() -> None:
    assert combined_lineage_hash("geo", "pop") == combined_lineage_hash("geo", "pop")
    assert combined_lineage_hash("geo", "pop") != combined_lineage_hash("pop", "geo")
