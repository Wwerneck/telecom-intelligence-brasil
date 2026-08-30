"""Interactive portfolio dashboard backed by audited broadband marts."""

from pathlib import Path

import plotly.express as px
import streamlit as st

from telecom_intelligence.analytics.dashboard_data import (
    available_periods,
    filter_period,
    format_decimal,
    format_integer,
    load_local_marts,
)

st.set_page_config(page_title="Telecom Intelligence Brasil", page_icon="📡", layout="wide")


@st.cache_data(show_spinner=False)
def load_data():
    return load_local_marts(Path("data/gold/marts"))


st.title("Telecom Intelligence Brasil")
st.caption("Banda larga fixa — dados oficiais ANATEL e população IBGE 2025")
try:
    marts = load_data()
except FileNotFoundError as error:
    st.error(f"Dados analíticos indisponíveis: {error}")
    st.stop()

national = marts["mart_broadband_national_monthly"]
period = st.sidebar.selectbox("Competência", available_periods(national))
national_month = filter_period(national, period).iloc[0]
st.sidebar.markdown("**Metodologia**")
st.sidebar.caption(
    "Acessos por 100 habitantes é densidade de linhas sobre a população IBGE 2025, "
    "não percentual de pessoas conectadas."
)

first, second, third, fourth = st.columns(4)
growth = national_month["accesses_month_over_month_pct"]
first.metric(
    "Acessos",
    format_integer(national_month["accesses"]),
    f"{format_decimal(growth)}% vs. mês anterior" if growth == growth else "Sem mês anterior",
)
second.metric(
    "Acessos / 100 habitantes",
    format_decimal(national_month["accesses_per_100_inhabitants"]),
)
third.metric("Participação da fibra", f"{format_decimal(national_month['fiber_share_pct'])}%")
fourth.metric(
    "Velocidade acima de 34 Mbps",
    f"{format_decimal(national_month['high_speed_share_pct'])}%",
)

st.subheader("Evolução nacional")
evolution = national.sort_values("date_key").copy()
evolution["competência"] = (
    evolution["reference_year"].astype(str)
    + "-"
    + evolution["reference_month"].astype(str).str.zfill(2)
)
st.plotly_chart(
    px.line(
        evolution,
        x="competência",
        y="accesses",
        markers=True,
        labels={"accesses": "Acessos"},
    ),
    width="stretch",
)

left, right = st.columns(2)
providers = filter_period(marts["mart_broadband_provider_monthly"], period).nlargest(15, "accesses")
left.subheader("Maiores prestadoras")
left.plotly_chart(
    px.bar(
        providers.sort_values("accesses"),
        x="accesses",
        y="company_name",
        orientation="h",
        labels={"accesses": "Acessos", "company_name": "Prestadora"},
    ),
    width="stretch",
)
technology = filter_period(marts["mart_broadband_technology_monthly"], period)
technology = technology.groupby("access_medium", as_index=False)["accesses"].sum()
right.subheader("Meio de acesso")
right.plotly_chart(
    px.pie(technology, names="access_medium", values="accesses", hole=0.45),
    width="stretch",
)

st.subheader("Faixas de velocidade")
speed = filter_period(marts["mart_broadband_speed_monthly"], period)
st.plotly_chart(
    px.bar(
        speed,
        x="speed_range",
        y="accesses",
        labels={"speed_range": "Faixa", "accesses": "Acessos"},
    ),
    width="stretch",
)

st.subheader("Municípios")
municipalities = filter_period(marts["mart_broadband_municipality_monthly"], period)
state = st.selectbox("UF", ["Todas", *sorted(municipalities["state_code"].unique().tolist())])
if state != "Todas":
    municipalities = municipalities.loc[municipalities["state_code"].eq(state)]
st.dataframe(
    municipalities.nlargest(100, "accesses")[
        [
            "municipality_name",
            "state_code",
            "accesses",
            "accesses_per_100_inhabitants",
            "fiber_share_pct",
            "companies",
        ]
    ],
    width="stretch",
    hide_index=True,
)
st.caption(
    f"Fonte: ANATEL, competência {period}. População: IBGE 2025. "
    "Pipeline auditável RAW → Bronze → Silver → Gold."
)
