from src.collectors.Climate import Climate
from src.collectors.Firms import Firms
from src.collectors.Vegetation import Vegetation
from src.processors.RiskProcessor import RiskProcessor
LAT, LON = -3.1190, -60.0217  ### valores especificos para regiao amazonica, isso sera configuravel diretamente no painel streamlit
DIAS_DE_FOCO = 5
def main():
    veg = Vegetation()
    climate = Climate()
    firms = Firms()

    print("Carregando dados geográficos...")
    gdf = veg.read_geo_data()

    municipio = veg.get_municipio(gdf, LAT, LON)
    if municipio is None:
        raise ValueError(f"Nenhum município encontrado para ({LAT}, {LON})")

    bioma = veg.get_bioma(municipio["uf"])

    print("Coletando dados climáticos...")
    df_clima = climate.get_data(LAT, LON)

    print("Coletando focos de incêndio...")
    df_focos = firms.get_focos(dias=DIAS_DE_FOCO)

    print("Processando risco...")
    df, resumo = RiskProcessor.process(df_clima, df_focos, bioma)

    print("\n--- RESULTADO ---")
    print(f"Município: {municipio['nome']} / {municipio['uf']}")
    print(f"Bioma : {resumo['bioma']}")
    print(f"Total focos : {resumo['total_focos']}")
    print(f"Temp média : {resumo['temp_media']}°C")
    print(f"Chuva média : {resumo['chuva_media']} mm")
    print(f"Índice risco: {resumo['indice_risco']} / 10")


if __name__ == "__main__":
    main()