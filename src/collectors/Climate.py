import requests
import pandas as pd
class Climate:
    def get_data(self, lat, lon):
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&daily=temperature_2m_max,precipitation_sum,windspeed_10m_max"
            f"&timezone=America/Sao_Paulo&past_days=30"
        )
        response = requests.get(url)
        response.raise_for_status()
        daily = response.json()["daily"]
        return self._to_dataframe(daily)

    def _to_dataframe(self, daily):
        df = pd.DataFrame({
            "date":            daily["time"],
            "temperature_max": daily["temperature_2m_max"],
            "precipitation":   daily["precipitation_sum"],
            "windspeed":       daily["windspeed_10m_max"],
        })
        df["date"] = pd.to_datetime(df["date"])
        return df
