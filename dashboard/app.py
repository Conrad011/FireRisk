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
    dias = st.slider("Janela FIRMS (dias)", min_value=1, max_value=5, value=5)
    analisar = st.button("🔍 Analisar", type="primary", use_container_width=True)
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
def load_firms(dias):
    return Firms().get_focos(dias=dias)

# ── Execução da análise ───────────────────────────────────────────────────────
if analisar or "resumo" not in st.session_state:
    try:
        gdf = load_geo()
        veg = Vegetation()
        municipio = veg.get_municipio(gdf, lat, lon)

        if municipio is None:
            st.error(f"Nenhum município encontrado para ({lat}, {lon}). Verifique as coordenadas.")
            st.stop()

        bioma = veg.get_bioma(municipio["uf"])
        df_clima = load_climate(lat, lon)
        df_focos = load_firms(dias)
        df, resumo = RiskProcessor.process(df_clima, df_focos, bioma)

        st.session_state.update({
            "resumo": resumo, "municipio": municipio,
            "df_clima": df_clima, "df_focos": df_focos,
            "df": df, "gdf": gdf, "lat": lat, "lon": lon,
        })

    except EnvironmentError as e:
        st.error(f"Variável de ambiente não configurada: {e}")
        st.info("Configure NASA_FIRMS_KEY no arquivo .env ou nas variáveis de ambiente.")
        st.stop()
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        st.stop()

if "resumo" not in st.session_state:
    st.info("Configure os parâmetros na barra lateral e clique em **Analisar**.")
    st.stop()

resumo    = st.session_state["resumo"]
municipio = st.session_state["municipio"]
df_clima  = st.session_state["df_clima"]
df_focos  = st.session_state["df_focos"]
df        = st.session_state["df"]
gdf       = st.session_state["gdf"]
lat_used  = st.session_state["lat"]
lon_used  = st.session_state["lon"]

# ── Métricas ──────────────────────────────────────────────────────────────────
indice = resumo["indice_risco"]
risco_label = "Alto" if indice >= 6 else "Moderado" if indice >= 3 else "Baixo"
risco_color = "inverse" if indice >= 6 else "off" if indice >= 3 else "normal"

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Município", municipio["nome"])
c2.metric("UF / Bioma", f"{municipio['uf']} · {resumo['bioma']}")
c3.metric("Índice de Risco", f"{indice} / 10", delta=risco_label, delta_color=risco_color)
c4.metric("Total de Focos", resumo["total_focos"])
c5.metric("Temp. Máx. Média", f"{resumo['temp_media']} °C")

st.divider()

# ── Mapa + Gauge ──────────────────────────────────────────────────────────────
col_map, col_gauge = st.columns([3, 1])

with col_map:
    st.subheader("Mapa de Focos de Calor")

    m = folium.Map(location=[lat_used, lon_used], zoom_start=6, tiles="CartoDB dark_matter")

    # Polígono do município
    mun_gdf = gdf[gdf["codarea"] == municipio["codarea"]]
    if not mun_gdf.empty:
        folium.GeoJson(
            mun_gdf.__geo_interface__,
            style_function=lambda _: {
                "fillColor": "#ff6b00", "color": "#ff9933",
                "weight": 2, "fillOpacity": 0.15,
            },
        ).add_to(m)

    # Heatmap dos focos ponderado por FRP
    if not df_focos.empty and "latitude" in df_focos.columns:
        heat_data = [
            [row["latitude"], row["longitude"], max(float(row.get("frp", 1)), 1)]
            for _, row in df_focos.iterrows()
        ]
        HeatMap(
            heat_data, radius=12, blur=8, min_opacity=0.4,
            gradient={"0.4": "blue", "0.65": "yellow", "1": "red"},
        ).add_to(m)

    # Marcador do ponto analisado
    folium.Marker(
        location=[lat_used, lon_used],
        popup=f"{municipio['nome']} ({lat_used:.4f}, {lon_used:.4f})",
        tooltip="Ponto analisado",
        icon=folium.Icon(color="red", icon="fire", prefix="fa"),
    ).add_to(m)

    st_folium(m, use_container_width=True, height=450)

with col_gauge:
    st.subheader("Índice de Risco")

    bar_color = "#ff4444" if indice >= 6 else "#ffaa00" if indice >= 3 else "#44cc44"
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=indice,
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

    peso_bioma = {"Amazônia": 1.5, "Cerrado": 1.2, "Caatinga": 1.3}
    peso = peso_bioma.get(resumo["bioma"], 1.0)
    st.info(f"**Bioma:** {resumo['bioma']}  \n**Multiplicador de risco:** {peso}×")

    if "confidence" in df_focos.columns and not df_focos.empty:
        conf_map = {"h": "Alta", "n": "Normal", "l": "Baixa"}
        st.caption("Confiança dos focos detectados:")
        for conf, count in df_focos["confidence"].value_counts().items():
            st.caption(f"  • {conf_map.get(conf, conf)}: **{count}**")

st.divider()

# ── Gráficos climáticos ───────────────────────────────────────────────────────
st.subheader("Série Climática — Últimos 30 dias")
col_clima, col_focos = st.columns(2)

with col_clima:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        x=df_clima["date"], y=df_clima["temperature_max"],
        name="Temp. Máx (°C)", line=dict(color="#ff4444", width=2),
        fill="tozeroy", fillcolor="rgba(255,68,68,0.1)",
    ), secondary_y=False)
    fig.add_trace(go.Bar(
        x=df_clima["date"], y=df_clima["precipitation"],
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

with col_focos:
    focos_dia = df.groupby("date")["total_focos"].sum().reset_index()
    fig2 = go.Figure(go.Bar(
        x=focos_dia["date"],
        y=focos_dia["total_focos"],
        marker_color=["#ff4444" if v > 0 else "#444" for v in focos_dia["total_focos"]],
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
            if c in df_focos.columns]
    st.dataframe(df_focos[cols].sort_values("acq_date", ascending=False), use_container_width=True)
