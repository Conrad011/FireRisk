from src.collectors.Climate import Climate
from src.collectors.Firms import Firms
from src.collectors.Vegetation import Vegetation
from src.processors.RiskProcessor import RiskProcessor
LAT, LON = -3.1190, -60.0217  ### valores especificos para regiao amazonica, isso sera configuravel diretamente no painel streamlit
FIRE_DAYS = 5
def main():
    veg = Vegetation()
    climate = Climate()
    firms = Firms()

    print("Carregando dados geográficos...")
    gdf = veg.read_geo_data()

    municipality = veg.get_municipality(gdf, LAT, LON)
    if municipality is None:
        raise ValueError(f"Nenhum município encontrado para ({LAT}, {LON})")

    biome = veg.get_biome(municipality["uf"])

    print("Coletando dados climáticos...")
    df_climate = climate.get_data(LAT, LON)

    print("Coletando focos de incêndio...")
    df_fires = firms.get_fires(days=FIRE_DAYS)

    print("Processando risco...")
    df, summary = RiskProcessor.process(df_climate, df_fires, biome)

    print("\n--- RESULTADO ---")
    print(f"Município: {municipality['nome']} / {municipality['uf']}")
    print(f"Bioma : {summary['biome']}")
    print(f"Total focos : {summary['total_fires']}")
    print(f"Temp média : {summary['avg_temp']}°C")
    print(f"Chuva média : {summary['avg_rain']} mm")
    print(f"Índice risco: {summary['risk_index']} / 10")


if __name__ == "__main__":
    main()
