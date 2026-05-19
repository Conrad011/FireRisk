import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.collectors.Climate import Climate
from src.collectors.Firms import Firms
from src.collectors.Vegetation import Vegetation
from src.processors.RiskProcessor import RiskProcessor

st.set_page_config(page_title="FireRisk", page_icon="🔥", layout="wide")

st.title("🔥 FireRisk — Monitor de Risco de Incêndio")
st.caption("NASA FIRMS (focos de calor) · Open-Meteo (clima) · IBGE (municípios)")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Parâmetros")
    lat = st.number_input("Latitude", value=-3.1190, format="%.4f", step=0.001)
    lon = st.number_input("Longitude", value=-60.0217, format="%.4f", step=0.001)
    days = st.slider("Janela FIRMS (dias)", min_value=1, max_value=5, value=5)
    analyze = st.button("🔍 Analisar", type="primary", use_container_width=True)
    st.divider()
    st.caption("Coordenada padrão: Manaus, AM")

# ── Cache de dados pesados ────────────────────────────────────────────────────
@st.cache_data(show_spinner="Carregando municípios (IBGE)...")
def load_geo():
    return Vegetation().read_geo_data()

@st.cache_data(show_spinner="Buscando clima (Open-Meteo)...")
def load_climate(lat, lon):
    return Climate().get_data(lat, lon)

@st.cache_data(show_spinner="Buscando focos (NASA FIRMS)...")
def load_firms(days):
    return Firms().get_fires(days=days)

# ── Execução da análise ───────────────────────────────────────────────────────
if analyze or "summary" not in st.session_state:
    try:
        gdf = load_geo()
        veg = Vegetation()
        municipality = veg.get_municipality(gdf, lat, lon)

        if municipality is None:
            st.error(f"Nenhum município encontrado para ({lat}, {lon}). Verifique as coordenadas.")
            st.stop()

        biome = veg.get_biome(municipality["uf"])
        df_climate = load_climate(lat, lon)
        df_fires = load_firms(days)
        df, summary = RiskProcessor.process(df_climate, df_fires, biome)

        st.session_state.update({
            "summary": summary, "municipality": municipality,
            "df_climate": df_climate, "df_fires": df_fires,
            "df": df, "gdf": gdf, "lat": lat, "lon": lon,
        })

    except EnvironmentError as e:
        st.error(f"Variável de ambiente não configurada: {e}")
        st.info("Configure NASA_FIRMS_KEY no arquivo .env ou nas variáveis de ambiente.")
        st.stop()
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        st.stop()

if "summary" not in st.session_state:
    st.info("Configure os parâmetros na barra lateral e clique em **Analisar**.")
    st.stop()

summary      = st.session_state["summary"]
municipality = st.session_state["municipality"]
df_climate   = st.session_state["df_climate"]
df_fires     = st.session_state["df_fires"]
df           = st.session_state["df"]
gdf          = st.session_state["gdf"]
lat_used     = st.session_state["lat"]
lon_used     = st.session_state["lon"]

# ── Métricas ──────────────────────────────────────────────────────────────────
risk_index = summary["risk_index"]
risk_label = "Alto" if risk_index >= 6 else "Moderado" if risk_index >= 3 else "Baixo"
risk_color = "inverse" if risk_index >= 6 else "off" if risk_index >= 3 else "normal"

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Município", municipality["nome"])
c2.metric("UF / Bioma", f"{municipality['uf']} · {summary['biome']}")
c3.metric("Índice de Risco", f"{risk_index} / 10", delta=risk_label, delta_color=risk_color)
c4.metric("Total de Focos", summary["total_fires"])
c5.metric("Temp. Máx. Média", f"{summary['avg_temp']} °C")

st.divider()

# ── Mapa + Gauge ──────────────────────────────────────────────────────────────
col_map, col_gauge = st.columns([3, 1])

with col_map:
    st.subheader("Mapa de Focos de Calor")

    m = folium.Map(location=[lat_used, lon_used], zoom_start=6, tiles="CartoDB dark_matter")

    # Polígono do município
    municipality_gdf = gdf[gdf["codarea"] == municipality["codarea"]]
    if not municipality_gdf.empty:
        folium.GeoJson(
            municipality_gdf.__geo_interface__,
            style_function=lambda _: {
                "fillColor": "#ff6b00", "color": "#ff9933",
                "weight": 2, "fillOpacity": 0.15,
            },
        ).add_to(m)

    # Heatmap dos focos ponderado por FRP
    if not df_fires.empty and "latitude" in df_fires.columns:
        heat_data = [
            [row["latitude"], row["longitude"], max(float(row.get("frp", 1)), 1)]
            for _, row in df_fires.iterrows()
        ]
        HeatMap(
            heat_data, radius=12, blur=8, min_opacity=0.4,
            gradient={"0.4": "blue", "0.65": "yellow", "1": "red"},
        ).add_to(m)

    # Marcador do ponto analisado
    folium.Marker(
        location=[lat_used, lon_used],
        popup=f"{municipality['nome']} ({lat_used:.4f}, {lon_used:.4f})",
        tooltip="Ponto analisado",
        icon=folium.Icon(color="red", icon="fire", prefix="fa"),
    ).add_to(m)

    st_folium(m, use_container_width=True, height=450)

with col_gauge:
    st.subheader("Índice de Risco")

    bar_color = "#ff4444" if risk_index >= 6 else "#ffaa00" if risk_index >= 3 else "#44cc44"
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=risk_index,
        number={"suffix": " / 10", "font": {"size": 28}},
        gauge={
            "axis": {"range": [0, 10], "tickwidth": 1, "tickcolor": "white"},
            "bar": {"color": bar_color},
            "steps": [
                {"range": [0, 3], "color": "#1a3a1a"},
                {"range": [3, 6], "color": "#3a2a00"},
                {"range": [6, 10], "color": "#3a0000"},
            ],
        },
    ))
    fig_gauge.update_layout(
        height=260, margin=dict(t=20, b=10, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)", font_color="white",
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

    biome_weight = {"Amazônia": 1.5, "Cerrado": 1.2, "Caatinga": 1.3}
    weight = biome_weight.get(summary["biome"], 1.0)
    st.info(f"**Bioma:** {summary['biome']}  \n**Multiplicador de risco:** {weight}×")

    if "confidence" in df_fires.columns and not df_fires.empty:
        confidence_map = {"h": "Alta", "n": "Normal", "l": "Baixa"}
        st.caption("Confiança dos focos detectados:")
        for conf, count in df_fires["confidence"].value_counts().items():
            st.caption(f"  • {confidence_map.get(conf, conf)}: **{count}**")

st.divider()

# ── Gráficos climáticos ───────────────────────────────────────────────────────
st.subheader("Série Climática — Últimos 30 dias")
col_climate, col_fires = st.columns(2)

with col_climate:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        x=df_climate["date"], y=df_climate["temperature_max"],
        name="Temp. Máx (°C)", line=dict(color="#ff4444", width=2),
        fill="tozeroy", fillcolor="rgba(255,68,68,0.1)",
    ), secondary_y=False)
    fig.add_trace(go.Bar(
        x=df_climate["date"], y=df_climate["precipitation"],
        name="Chuva (mm)", marker_color="rgba(68,136,255,0.5)",
    ), secondary_y=True)
    fig.update_layout(
        title="Temperatura e Precipitação",
        height=320, paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", font_color="white",
        legend=dict(orientation="h", y=-0.25),
        margin=dict(t=40, b=50),
    )
    fig.update_yaxes(title_text="°C", secondary_y=False, gridcolor="#333")
    fig.update_yaxes(title_text="mm", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)

with col_fires:
    fires_per_day = df.groupby("date")["total_fires"].sum().reset_index()
    fig2 = go.Figure(go.Bar(
        x=fires_per_day["date"],
        y=fires_per_day["total_fires"],
        marker_color=["#ff4444" if v > 0 else "#444" for v in fires_per_day["total_fires"]],
    ))
    fig2.update_layout(
        title="Focos por Dia (Amazônia Legal)",
        height=320, paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", font_color="white",
        margin=dict(t=40, b=50),
    )
    fig2.update_xaxes(gridcolor="#333")
    fig2.update_yaxes(gridcolor="#333", title_text="Focos")
    st.plotly_chart(fig2, use_container_width=True)

# ── Tabela de focos ───────────────────────────────────────────────────────────
with st.expander("Ver dados brutos dos focos (NASA FIRMS)"):
    cols = [c for c in ["acq_date", "latitude", "longitude", "frp", "confidence", "daynight", "bright_ti4"]
            if c in df_fires.columns]
    st.dataframe(df_fires[cols].sort_values("acq_date", ascending=False), use_container_width=True)
