from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from telecom_intelligence.transformation.broadband_silver import (
    load_silver_contract,
    validate_and_aggregate_broadband,
)


def bronze_row(accesses: int, state_code: str = "GO") -> dict:
    return {
        "reference_year": 2026,
        "reference_month": 6,
        "economic_group": "OUTROS",
        "company_name": "EMPRESA",
        "company_cnpj": "00123456000199",
        "provider_size": "Pequeno Porte",
        "state_code": state_code,
        "municipality_name": "Nome antigo",
        "ibge_code": 5208707,
        "speed_range": "> 34Mbps",
        "speed_mbps": 100.0,
        "technology": "FTTH",
        "access_medium": "Fibra",
        "person_type": "Pessoa Física",
        "product_type": "INTERNET",
        "accesses": accesses,
        "_source_file": "raw.csv",
        "_ingestion_timestamp": "2026-08-28T22:00:00+00:00",
        "_pipeline_run_id": "run-1",
        "_sha256": "a" * 64,
        "_reference_date": "2026",
        "_schema_version": 1,
    }


def municipality_dimension() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "municipality_id": 1,
                "ibge_code": 5208707,
                "municipality_name": "Goiânia",
                "state_code": "GO",
            }
        ]
    )


def test_aggregates_duplicate_grain_and_canonicalizes_municipality() -> None:
    bronze = pd.DataFrame([bronze_row(10), bronze_row(15)])
    contract = load_silver_contract(Path("config/schemas/fixed_broadband_accesses_silver.yml"))

    silver, rejected = validate_and_aggregate_broadband(
        bronze, municipality_dimension(), contract, datetime(2026, 8, 29, tzinfo=UTC)
    )

    assert rejected.empty
    assert len(silver) == 1
    assert silver.loc[0, "accesses"] == 25
    assert silver.loc[0, "source_row_count"] == 2
    assert silver.loc[0, "municipality_name"] == "Goiânia"
    assert silver.loc[0, "municipality_name_source"] == "Nome antigo"


def test_quarantines_geographic_and_measure_violations() -> None:
    bronze = pd.DataFrame([bronze_row(0, state_code="DF")])
    contract = load_silver_contract(Path("config/schemas/fixed_broadband_accesses_silver.yml"))

    silver, rejected = validate_and_aggregate_broadband(bronze, municipality_dimension(), contract)

    assert silver.empty
    assert rejected["rejection_reason"].tolist() == ["invalid_accesses|state_code_mismatch"]


def test_quarantines_speed_outside_declared_range() -> None:
    row = bronze_row(10)
    row["speed_range"] = "0Kbps a 512Kbps"
    bronze = pd.DataFrame([row])
    contract = load_silver_contract(Path("config/schemas/fixed_broadband_accesses_silver.yml"))

    silver, rejected = validate_and_aggregate_broadband(bronze, municipality_dimension(), contract)

    assert silver.empty
    assert rejected["rejection_reason"].tolist() == ["speed_outside_range"]
