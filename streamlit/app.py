"""Interactive portfolio dashboard backed by audited broadband marts."""

import sys
from pathlib import Path

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from telecom_intelligence.analytics.dashboard_data import (  # noqa: E402
    available_periods,
    filter_period,
    format_decimal,
    format_integer,
    load_local_marts,
    prepare_access_medium_chart,
    prepare_evolution_chart,
    prepare_municipality_table,
    prepare_provider_chart,
    prepare_speed_chart,
)

st.set_page_config(
    page_title="Telecom Intelligence Brasil",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    f"<style>{(PROJECT_ROOT / 'streamlit/styles.css').read_text(encoding='utf-8')}</style>",
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_data():
    return load_local_marts(PROJECT_ROOT / "data/gold/marts")


st.markdown(
    """
    <section class="hero">
        <span class="hero-kicker">● Inteligência de mercado</span>
        <h1>Telecom Intelligence Brasil</h1>
        <p>Panorama executivo da banda larga fixa no Brasil</p>
        <div class="hero-source">Dados oficiais consolidados<br><strong>ANATEL + IBGE</strong></div>
    </section>
    """,
    unsafe_allow_html=True,
)
st.caption("Banda larga fixa — dados oficiais ANATEL e população IBGE 2025")
try:
    marts = load_data()
except FileNotFoundError as error:
    st.error(f"Dados analíticos indisponíveis: {error}")
    st.stop()

national = marts["mart_broadband_national_monthly"]
st.markdown(
    '<div class="section-label">Visão geral</div>'
    '<div class="section-title">Filtros e contexto</div>',
    unsafe_allow_html=True,
)
with st.container(border=True):
    period_column, coverage_column, companies_column, population_column = st.columns(
        [1.35, 1, 1, 1.15]
    )
    with period_column:
        period = st.selectbox(
            "Competência analisada",
            available_periods(national),
            help="Mês de referência da fotografia de acessos publicada pela ANATEL.",
        )

    national_month = filter_period(national, period).iloc[0]
    with coverage_column:
        st.metric(
            "Municípios observados",
            format_integer(national_month["municipalities_with_access"]),
            help="Municípios com ao menos um registro na competência selecionada.",
        )
    with companies_column:
        st.metric(
            "CNPJs de prestadoras",
            format_integer(national_month["companies"]),
            help="Quantidade de CNPJs distintos presentes na fonte ANATEL.",
        )
    with population_column:
        st.metric(
            "População de referência",
            format_integer(national_month["population"]),
            f"IBGE {int(national_month['population_reference_year'])}",
            help="População municipal usada apenas no cálculo de densidade.",
        )

    with st.expander("Metodologia, fontes e limitações dos indicadores"):
        methodology_left, methodology_right = st.columns(2)
        methodology_left.markdown(
            """
            **Fontes oficiais**

            - Acessos de banda larga fixa: ANATEL.
            - População municipal: IBGE, estimativa de 2025.
            - Geografia e nomes municipais: diretório oficial do IBGE.

            **Periodicidade**

            Cada competência representa uma fotografia mensal. Somar meses não produz um
            estoque anual válido.
            """
        )
        methodology_right.markdown(
            """
            **Interpretação**

            - “Acessos” representa linhas/contratos informados, não pessoas únicas.
            - “Acessos por 100 habitantes” é uma densidade sobre a população.
            - O numerador inclui os tipos de pessoa e produto existentes na fonte.
            - Participações são calculadas dentro da competência selecionada.
            """
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
evolution = prepare_evolution_chart(national)
selected_key = int(national_month["date_key"])
selected = evolution.loc[evolution["date_key"].eq(selected_key)].iloc[0]
evolution_chart = go.Figure()
evolution_chart.add_trace(
    go.Scatter(
        x=evolution["Competência"],
        y=evolution["Acessos (milhões)"],
        mode="lines+markers+text",
        text=evolution["Rótulo"],
        textposition="top center",
        textfont={"size": 12, "color": "#52677F"},
        line={"color": "#1473C9", "width": 3, "shape": "spline", "smoothing": 0.65},
        marker={"size": 9, "color": "white", "line": {"color": "#1473C9", "width": 3}},
        fill="tozeroy",
        fillcolor="rgba(20, 115, 201, 0.10)",
        customdata=evolution[["Acessos formatados", "Variação mensal"]],
        hovertemplate=(
            "<b>%{x}</b><br>Acessos: %{customdata[0]}<br>Variação mensal: "
            "%{customdata[1]}<extra></extra>"
        ),
    )
)
evolution_chart.add_trace(
    go.Scatter(
        x=[selected["Competência"]],
        y=[selected["Acessos (milhões)"]],
        mode="markers",
        marker={"size": 15, "color": "#F2A900", "line": {"color": "white", "width": 3}},
        hoverinfo="skip",
        showlegend=False,
    )
)
minimum = evolution["Acessos (milhões)"].min()
maximum = evolution["Acessos (milhões)"].max()
padding = max((maximum - minimum) * 0.28, 0.15)
tick_values = [minimum, (minimum + maximum) / 2, maximum]
evolution_chart.update_layout(
    height=440,
    margin={"l": 15, "r": 30, "t": 30, "b": 15},
    plot_bgcolor="white",
    showlegend=False,
    hovermode="x unified",
    font={"family": "Arial, sans-serif", "color": "#26364A"},
    xaxis={
        "title": None,
        "showgrid": False,
        "showline": True,
        "linecolor": "#D7E1EC",
        "tickfont": {"size": 12, "color": "#52677F"},
    },
    yaxis={
        "title": "Acessos (milhões)",
        "range": [minimum - padding, maximum + padding],
        "tickvals": tick_values,
        "ticktext": [format_decimal(value, 2) for value in tick_values],
        "showgrid": True,
        "gridcolor": "#E8EEF5",
        "zeroline": False,
    },
)
evolution_chart.add_annotation(
    x=selected["Competência"],
    y=selected["Acessos (milhões)"],
    text="Competência selecionada",
    showarrow=True,
    arrowhead=2,
    arrowcolor="#C38400",
    ax=0,
    ay=55,
    bgcolor="#FFF4D6",
    bordercolor="#F2A900",
    borderpad=6,
    font={"size": 11, "color": "#775500"},
)
st.plotly_chart(evolution_chart, width="stretch", config={"displayModeBar": False})
st.caption(
    "Evolução do estoque mensal de acessos. A escala vertical é ajustada para evidenciar a "
    "variação entre competências."
)

left, right = st.columns(2)
providers = prepare_provider_chart(filter_period(marts["mart_broadband_provider_monthly"], period))
left.subheader("Líderes de mercado")
provider_chart = px.bar(
    providers,
    x="accesses",
    y="Prestadora",
    orientation="h",
    text="Participação",
    custom_data=["Acessos formatados"],
)
provider_colors = ["#BFD6EA"] * len(providers)
provider_colors[-3:] = ["#4F93C8", "#1F6FAE", "#07599C"]
provider_chart.update_traces(
    marker_color=provider_colors,
    textposition="outside",
    cliponaxis=False,
    hovertemplate=(
        "<b>%{y}</b><br>Acessos: %{customdata[0]}<br>Participação: %{text}<extra></extra>"
    ),
)
provider_chart.update_layout(
    height=500,
    margin={"l": 10, "r": 70, "t": 10, "b": 10},
    plot_bgcolor="white",
    showlegend=False,
    font={"family": "Arial, sans-serif", "color": "#26364A"},
    xaxis={
        "range": [0, providers["accesses"].max() * 1.18],
        "showgrid": True,
        "gridcolor": "#E8EEF5",
        "zeroline": False,
        "title": "Total de acessos",
        "tickformat": "~s",
    },
    yaxis={"title": None, "showgrid": False},
)
left.plotly_chart(provider_chart, width="stretch", config={"displayModeBar": False})
left.caption("Top 10 prestadoras, com CNPJs consolidados pelo nome da empresa.")

technology = prepare_access_medium_chart(
    filter_period(marts["mart_broadband_technology_monthly"], period)
)
right.subheader("Tecnologia de acesso")
technology_chart = px.bar(
    technology,
    x="Participação no total (%)",
    y="Meio de acesso",
    orientation="h",
    text="Participação",
    custom_data=["Acessos formatados"],
)
medium_colors = {
    "Fibra": "#07599C",
    "Cabo Coaxial": "#3987C5",
    "Rádio": "#60AAA8",
    "Satélite": "#94C8D8",
    "Cabo Metálico": "#BDD3E5",
}
technology_chart.update_traces(
    marker_color=[medium_colors.get(value, "#9FB6C9") for value in technology["Meio de acesso"]],
    textposition="outside",
    cliponaxis=False,
    hovertemplate=(
        "<b>%{y}</b><br>Participação: %{text}<br>Acessos: %{customdata[0]}<extra></extra>"
    ),
)
technology_chart.update_layout(
    height=500,
    margin={"l": 10, "r": 70, "t": 10, "b": 10},
    plot_bgcolor="white",
    showlegend=False,
    font={"family": "Arial, sans-serif", "color": "#26364A"},
    xaxis={
        "range": [0, technology["Participação no total (%)"].max() * 1.18],
        "ticksuffix": "%",
        "showgrid": True,
        "gridcolor": "#E8EEF5",
        "zeroline": False,
        "title": "Participação no total de acessos",
    },
    yaxis={"title": None, "showgrid": False},
)
right.plotly_chart(technology_chart, width="stretch", config={"displayModeBar": False})
right.caption("Distribuição mensal por infraestrutura de acesso.")

st.subheader("Faixas de velocidade")
speed = prepare_speed_chart(filter_period(marts["mart_broadband_speed_monthly"], period))
speed_chart = px.bar(
    speed,
    x="Participação no total (%)",
    y="Faixa de velocidade",
    orientation="h",
    text="Participação",
    custom_data=["Acessos formatados"],
    color="Faixa de velocidade",
    color_discrete_sequence=["#DCEBFA", "#B8D8F4", "#83B9E8", "#438FD0", "#07599C"],
    category_orders={"Faixa de velocidade": list(reversed(speed["Faixa de velocidade"].tolist()))},
)
speed_chart.update_traces(
    textposition="outside",
    cliponaxis=False,
    hovertemplate=(
        "<b>%{y}</b><br>Participação: %{text}<br>Acessos: %{customdata[0]}<extra></extra>"
    ),
)
speed_chart.update_layout(
    showlegend=False,
    height=410,
    margin={"l": 10, "r": 70, "t": 10, "b": 10},
    plot_bgcolor="white",
    font={"family": "Arial, sans-serif", "color": "#26364A"},
    xaxis={
        "range": [0, max(speed["Participação no total (%)"].max() * 1.12, 10)],
        "ticksuffix": "%",
        "showgrid": True,
        "gridcolor": "#E8EEF5",
        "zeroline": False,
        "title": "Participação no total de acessos",
    },
    yaxis={"title": None, "showgrid": False},
)
st.plotly_chart(speed_chart, width="stretch", config={"displayModeBar": False})
st.caption(
    "Distribuição dos acessos por faixa de velocidade. Passe o cursor sobre uma barra para ver "
    "a quantidade absoluta."
)

st.subheader("Municípios")
municipalities = filter_period(marts["mart_broadband_municipality_monthly"], period)
state = st.selectbox("UF", ["Todas", *sorted(municipalities["state_code"].unique().tolist())])
if state != "Todas":
    municipalities = municipalities.loc[municipalities["state_code"].eq(state)]
st.dataframe(
    prepare_municipality_table(municipalities.nlargest(100, "accesses")),
    width="stretch",
    hide_index=True,
)
st.caption(
    f"Fonte: ANATEL, competência {period}. População: IBGE 2025. "
    "Pipeline auditável RAW → Bronze → Silver → Gold."
)
