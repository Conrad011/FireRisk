# FireRisk

Real-time wildfire risk monitor for the Brazilian Amazon. Combines NASA satellite fire detections, daily weather data, and IBGE municipal boundaries to compute a per-location risk index and display it on an interactive dashboard.

![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![Streamlit](https://img.shields.io/badge/dashboard-streamlit-red) ![License](https://img.shields.io/badge/license-MIT-green)

---

## How it works

1. **Collectors** pull data from three public APIs:
   - `Climate` — 30-day weather history from [Open-Meteo](https://open-meteo.com/) (max temperature, precipitation, wind speed)
   - `Firms` — active fire hotspots from [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) (VIIRS SNPP NRT, Amazon bounding box)
   - `Vegetation` — municipality polygons and state-to-biome mapping from [IBGE](https://servicodados.ibge.gov.br/)

2. **RiskProcessor** merges the datasets and computes a 0–10 risk index:

   ```
   fire_score    = clamp(hotspot_count / 100, 0, 1)
   climate_score = clamp(avg_max_temp / 40, 0, 1) × clamp(1 − avg_rain / 50, 0, 1)
   risk_index    = (fire_score × 0.6 + climate_score × 0.4) × biome_weight × 10
   ```

   Biome multipliers: Amazônia ×1.5 · Cerrado ×1.2 · Caatinga ×1.3

3. **Dashboard** (`streamlit`) renders an interactive heatmap, risk gauge, and climate time series.

---

## Project structure

```
FireRisk/
├── main.py                   # CLI entry point
├── requirements.txt
├── .env                      # secrets (see Configuration)
├── dashboard/
│   └── app.py                # Streamlit dashboard
├── data/
│   ├── raw/                  # municipios.geojson (git-ignored)
│   └── processed/
└── src/
    ├── collectors/
    │   ├── Climate.py
    │   ├── Firms.py
    │   └── Vegetation.py
    ├── models/
    │   └── randomForest.py   # in progress
    └── processors/
        └── RiskProcessor.py
```

---

## Requirements

- Python 3.10+
- A free [NASA FIRMS API key](https://firms.modaps.eosdis.nasa.gov/api/area/)

---

## Installation

```bash
git clone https://github.com/your-username/FireRisk.git
cd FireRisk
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## Configuration

Create a `.env` file in the project root:

```env
NASA_FIRMS_KEY=your_api_key_here
```

The geographic data file (`municipios.geojson`) is downloaded automatically on first run via the IBGE API and saved to `data/raw/`. The path is currently hardcoded in `Vegetation.py` and will be made configurable via `.env` in a future update.

---

## Usage

### CLI

Runs a single analysis for the configured coordinates and prints the result:

```bash
python main.py
```

Default coordinates: Manaus, AM (`-3.1190, -60.0217`). Edit `LAT`, `LON`, and `FIRE_DAYS` at the top of `main.py` to change them.

**Example output:**

```
Carregando dados geográficos...
Coletando dados climáticos...
Coletando focos de incêndio...
Processando risco...

--- RESULTADO ---
Município: Manaus / AM
Bioma : Amazônia
Total focos : 47
Temp média : 31.4°C
Chuva média : 6.2 mm
Índice risco: 7.83 / 10
```

### Dashboard

```bash
streamlit run dashboard/app.py
```

Opens at `http://localhost:8501`. Use the sidebar to set coordinates and the FIRMS time window (1–5 days), then click **Analisar**.

Dashboard features:
- Interactive fire heatmap (Folium + FRP-weighted intensity)
- Municipality polygon overlay
- Risk gauge (0–10)
- 30-day temperature and precipitation chart
- Daily fire count bar chart
- Raw FIRMS data table

---

## Data sources

| Source | Data | License |
|--------|------|---------|
| [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) | VIIRS SNPP NRT active fire detections | NASA Open Data |
| [Open-Meteo](https://open-meteo.com/) | Daily weather forecast & history | CC BY 4.0 |
| [IBGE](https://servicodados.ibge.gov.br/) | Municipality boundaries & metadata | Open Government Data |

---

## Roadmap

- [ ] Random Forest classifier trained on historical fire/climate data
- [ ] Configurable coordinates and paths via `.env`
- [ ] Alert system for high-risk events
- [ ] Support for additional biomes and regions

---

## License

MIT
