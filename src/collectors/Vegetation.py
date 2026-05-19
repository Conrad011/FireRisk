import requests
from pathlib import Path
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point


class Vegetation:

    _GEOJSON_PATH = Path(r"C:\Dev\FireRisk\data\raw\municipios.geojson") #Os dados usados aqui de maneira fixa configuram-se apenas para fins de teste, assim que for tudo finalizado, eu os colocarei no .env


    _BIOMES_BY_STATE = {
        "AM": "Amazônia", "PA": "Amazônia", "RO": "Amazônia",
        "AC": "Amazônia", "RR": "Amazônia", "AP": "Amazônia",
        "TO": "Cerrado",  "MT": "Amazônia", "MA": "Amazônia",
        "GO": "Cerrado",  "MS": "Pantanal", "MG": "Cerrado",
        "BA": "Caatinga", "CE": "Caatinga", "PE": "Caatinga",
    }

    def download(self):
        url = (
            "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
            "?formato=application/vnd.geo+json&qualidade=minima&intrarregiao=municipio"
        )
        response = requests.get(url)
        response.raise_for_status()
        self._GEOJSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._GEOJSON_PATH.write_text(response.text)

    def read_geo_data(self):
        gdf = gpd.read_file(self._GEOJSON_PATH)
        resp = requests.get("https://servicodados.ibge.gov.br/api/v1/localidades/municipios")
        resp.raise_for_status()
        df_names = pd.DataFrame([{
            "codarea": str(m["id"]),
            "nome": m["nome"],
            "uf": m["regiao-imediata"]["regiao-intermediaria"]["UF"]["sigla"],
        } for m in resp.json()])
        return gdf.merge(df_names, on="codarea", how="left")

    def get_municipality(self, gdf, lat, lon):
        point = Point(lon, lat)
        for _, row in gdf.iterrows():
            if row["geometry"].contains(point):
                return {
                    "codarea": row["codarea"],
                    "nome": row["nome"],
                    "uf": row["uf"],
                }
        return None

    def get_biome(self, uf):
        return self._BIOMES_BY_STATE.get(uf, "Desconhecido")
