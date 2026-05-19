import os
import requests
import pandas as pd
from io import StringIO


class Firms:

    _BBOX_AMAZON = "-74,-18,-44,5"

    def __init__(self):
        self._api_key = os.getenv("NASA_FIRMS_KEY")
        if not self._api_key:
            raise EnvironmentError("Variável de ambiente NASA_FIRMS_KEY não definida.")

    def get_fires(self, days=5):
        url = (
            f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
            f"{self._api_key}/VIIRS_SNPP_NRT/"
            f"{self._BBOX_AMAZON}/{days}"
        )
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Erro da API FIRMS: {response.status_code} - {response.text[:300]}")
        return pd.read_csv(StringIO(response.text))
