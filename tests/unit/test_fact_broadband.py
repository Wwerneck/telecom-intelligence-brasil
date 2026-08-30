import pandas as pd
import pytest

from telecom_intelligence.transformation.fact_broadband import (
    FACT_GRAIN,
    build_broadband_fact,
    build_fact_frame,
    build_monthly_date_dimension,
)


def silver_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "reference_year": 2026,
                "reference_month": 6,
                "economic_group": "OUTROS",
                "company_name": "EMPRESA",
                "company_cnpj": "00123456000199",
                "provider_size": "Pequeno Porte",
                "state_code": "GO",
                "ibge_code": 5208707,
                "municipality_id": 5208707,
                "speed_range": "> 34Mbps",
                "speed_mbps": 100.0,
                "technology": "FTTH",
                "access_medium": "Fibra",
                "person_type": "Pessoa Física",
                "product_type": "INTERNET",
                "accesses": 25,
                "source_row_count": 2,
                "_source_file": "raw.csv",
                "_pipeline_run_id": "run-1",
                "_sha256": "a" * 64,
                "_silver_schema_version": 1,
            }
        ]
    )


def dimensions() -> tuple[pd.DataFrame, pd.DataFrame]:
    municipalities = pd.DataFrame([{"municipality_id": 5208707, "ibge_code": 5208707}])
    dates = build_monthly_date_dimension(silver_frame())
    return municipalities, dates


def test_fact_preserves_grain_measures_and_foreign_keys() -> None:
    municipalities, dates = dimensions()

    fact = build_fact_frame(silver_frame(), municipalities, dates)

    assert len(fact) == 1
    assert fact.loc[0, "date_key"] == 20260601
    assert fact.loc[0, "municipality_id"] == 5208707
    assert fact.loc[0, "accesses"] == 25
    assert fact.loc[0, "source_row_count"] == 2
    assert not fact.duplicated(FACT_GRAIN).any()


def test_fact_rejects_missing_municipality_foreign_key() -> None:
    _, dates = dimensions()

    with pytest.raises(ValueError, match="foreign-key gaps"):
        build_fact_frame(
            silver_frame(),
            pd.DataFrame(columns=["municipality_id", "ibge_code"]),
            dates,
        )


def test_fact_rejects_silver_grain_violation() -> None:
    municipalities, dates = dimensions()
    duplicated = pd.concat([silver_frame(), silver_frame()], ignore_index=True)

    with pytest.raises(ValueError, match="Silver grain violation"):
        build_fact_frame(duplicated, municipalities, dates)


def test_monthly_date_dimension_has_one_row_per_period() -> None:
    source = pd.concat([silver_frame(), silver_frame()], ignore_index=True)

    dimension = build_monthly_date_dimension(source)

    assert dimension.to_dict("records")[0]["year_month"] == "2026-06"
    assert len(dimension) == 1


def test_partitioned_fact_write_is_idempotent(tmp_path) -> None:
    silver_path = tmp_path / "silver.parquet"
    municipality_path = tmp_path / "municipality.parquet"
    silver_frame().to_parquet(silver_path, index=False)
    dimensions()[0].to_parquet(municipality_path, index=False)

    first = build_broadband_fact([silver_path], municipality_path, tmp_path / "gold")
    second = build_broadband_fact([silver_path], municipality_path, tmp_path / "gold")

    assert first.created is True
    assert second.created is False
    assert first.records_output == 1
    assert first.accesses_output == 25
