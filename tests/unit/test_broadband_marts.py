import pandas as pd
import pytest

from telecom_intelligence.analytics.broadband_marts import build_month_marts


def fact_frame() -> pd.DataFrame:
    base = {
        "date_key": 20260601,
        "reference_year": 2026,
        "reference_month": 6,
        "economic_group": "OUTROS",
        "company_name": "EMPRESA",
        "company_cnpj": "00123456000199",
        "provider_size": "Pequeno Porte",
        "speed_range": "> 34Mbps",
        "speed_mbps": 100.0,
        "technology": "FTTH",
        "access_medium": "Fibra",
        "person_type": "Pessoa Física",
        "product_type": "INTERNET",
        "source_row_count": 1,
    }
    return pd.DataFrame(
        [
            {**base, "municipality_id": 1, "ibge_code": 1000001, "accesses": 20},
            {**base, "municipality_id": 2, "ibge_code": 1000002, "accesses": 30},
        ]
    )


def municipality_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "municipality_id": 1,
                "ibge_code": 1000001,
                "municipality_name": "A",
                "state_code": "AA",
                "state_name": "Estado A",
                "region_name": "Região",
                "population": 100,
                "population_reference_year": 2025,
            },
            {
                "municipality_id": 2,
                "ibge_code": 1000002,
                "municipality_name": "B",
                "state_code": "AA",
                "state_name": "Estado A",
                "region_name": "Região",
                "population": 400,
                "population_reference_year": 2025,
            },
        ]
    )


def test_marts_reconcile_and_population_is_not_multiplied() -> None:
    marts = build_month_marts(fact_frame(), municipality_frame())
    national = marts["mart_broadband_national_monthly"].iloc[0]
    municipality = marts["mart_broadband_municipality_monthly"]

    assert national["accesses"] == 50
    assert national["population"] == 500
    assert national["accesses_per_100_inhabitants"] == 10
    assert municipality["accesses"].sum() == 50
    assert municipality.set_index("municipality_id").loc[1, "accesses_per_100_inhabitants"] == 20


def test_dimension_shares_sum_to_one_hundred() -> None:
    marts = build_month_marts(fact_frame(), municipality_frame())

    assert marts["mart_broadband_provider_monthly"]["market_share_pct"].sum() == 100
    assert marts["mart_broadband_technology_monthly"]["technology_share_pct"].sum() == 100
    assert marts["mart_broadband_speed_monthly"]["speed_range_share_pct"].sum() == 100


def test_rejects_duplicate_fact_grain() -> None:
    duplicated = pd.concat([fact_frame(), fact_frame().iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="Fact grain violation"):
        build_month_marts(duplicated, municipality_frame())
