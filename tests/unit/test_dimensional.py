from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from telecom_intelligence.transformation.dimensional import (
    build_dim_date,
    build_dim_municipality,
    build_dimensions,
)


def silver_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ibge_code": 5200050,
                "municipality_name": "Abadia de Goiás",
                "municipality_key": "abadia_de_goias",
                "state_id": 52,
                "state_code": "GO",
                "state_name": "Goiás",
                "region_id": 5,
                "region_code": "CO",
                "region_name": "Centro-Oeste",
                "immediate_region_id": 520001,
                "immediate_region_name": "Goiânia",
                "intermediate_region_id": 5201,
                "intermediate_region_name": "Goiânia",
                "legacy_microregion_id": 52010,
                "legacy_microregion_name": "Goiânia",
                "legacy_mesoregion_id": 5203,
                "legacy_mesoregion_name": "Centro Goiano",
                "_reference_date": "2026-08-28",
                "_sha256": "a" * 64,
            }
        ]
    )


def test_dim_municipality_has_documented_grain_and_no_invented_population() -> None:
    dimension = build_dim_municipality(silver_frame())

    assert dimension["municipality_id"].is_unique
    assert dimension.loc[0, "municipality_id"] == 5200050
    assert pd.isna(dimension.loc[0, "population"])
    assert pd.isna(dimension.loc[0, "population_reference_year"])


def test_dim_municipality_enriches_population_by_ibge_code() -> None:
    population = pd.DataFrame(
        [
            {
                "ibge_code": 5200050,
                "population": 1000,
                "population_reference_year": 2025,
                "_sha256": "b" * 64,
            }
        ]
    )

    dimension = build_dim_municipality(silver_frame(), population)

    assert dimension.loc[0, "population"] == 1000
    assert dimension.loc[0, "population_reference_year"] == 2025
    assert dimension.loc[0, "population_source_sha256"] == "b" * 64


def test_dim_municipality_rejects_grain_violation() -> None:
    duplicated = pd.concat([silver_frame(), silver_frame()], ignore_index=True)

    try:
        build_dim_municipality(duplicated)
    except ValueError as error:
        assert "grain violation" in str(error)
    else:
        raise AssertionError("Expected grain violation")


def test_dim_date_derives_expected_attributes() -> None:
    dimension = build_dim_date(pd.Series(["2026-08-28", "2026-08-28"]))

    assert dimension.to_dict("records") == [
        {
            "date_key": 20260828,
            "date": dimension.loc[0, "date"],
            "year": 2026,
            "quarter": 3,
            "month": 8,
            "month_name": "agosto",
            "year_month": "2026-08",
        }
    ]


def test_dimension_write_is_idempotent(tmp_path: Path) -> None:
    silver_path = tmp_path / "silver.parquet"
    silver_frame().to_parquet(silver_path, index=False)

    first = build_dimensions(silver_path, tmp_path / "gold")
    second = build_dimensions(silver_path, tmp_path / "gold")

    assert first.created is True
    assert second.created is False
    assert pq.read_table(first.municipality_path).num_rows == 1
    assert pq.read_metadata(first.municipality_path).metadata[b"model"] == b"dim_municipality"
