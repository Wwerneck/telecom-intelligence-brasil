from datetime import UTC, datetime

import pandas as pd

from telecom_intelligence.transformation.silver import transform_frame
from telecom_intelligence.transformation.text import matching_key, normalize_display_text


def contract() -> dict:
    return {
        "version": 1,
        "primary_key": "ibge_code",
        "required_columns": [
            "ibge_code",
            "municipality_name",
            "municipality_key",
            "state_code",
            "region_name",
        ],
        "accepted_values": {
            "state_code": ["GO", "MT"],
            "region_name": ["Centro-Oeste"],
        },
    }


def bronze_row(**overrides: object) -> dict:
    row = {
        "ibge_code": 5200050,
        "municipality_name": "Abadia de Goiás",
        "state_code": "GO",
        "region_name": "Centro-Oeste",
        "_source_file": "municipios",
        "_pipeline_run_id": "run-1",
    }
    row.update(overrides)
    return row


def test_text_normalization_preserves_display_accents() -> None:
    assert normalize_display_text("  São\u200b   José  ") == "São José"
    assert matching_key("São José") == "sao_jose"


def test_valid_record_reaches_silver() -> None:
    valid, rejected = transform_frame(
        pd.DataFrame([bronze_row()]), contract(), datetime(2026, 8, 28, tzinfo=UTC)
    )

    assert len(valid) == 1
    assert valid.loc[0, "municipality_key"] == "abadia_de_goias"
    assert rejected.empty


def test_invalid_and_duplicate_records_are_quarantined() -> None:
    frame = pd.DataFrame(
        [
            bronze_row(),
            bronze_row(municipality_name="Outro nome"),
            bronze_row(ibge_code=1, state_code="XX"),
        ]
    )

    valid, rejected = transform_frame(frame, contract())

    assert valid.empty
    assert len(rejected) == 3
    assert "duplicate_key" in rejected.loc[0, "rejection_reason"]
    assert "invalid_ibge_code" in rejected.loc[2, "rejection_reason"]
    assert "invalid_state_code" in rejected.loc[2, "rejection_reason"]
