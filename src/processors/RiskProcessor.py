import pandas as pd

class RiskProcessor:
    @staticmethod
    def process(climate_df, firms_df, bioma="Desconhecido"):
        firms_df = firms_df.rename(columns={"acq_date": "date"})
        climate_df["date"] = pd.to_datetime(climate_df["date"])
        firms_df["date"] = pd.to_datetime(firms_df["date"])

        focos_por_dia = firms_df.groupby("date").size().reset_index(name="total_focos")
        df = climate_df.merge(focos_por_dia, on="date", how="left")
        df["total_focos"] = df["total_focos"].fillna(0)
        df["teve_foco"] = (df["total_focos"] > 0).astype(int)

        # índice de risco
        peso_bioma = {"Amazônia": 1.5, "Cerrado": 1.2, "Caatinga": 1.3}
        peso = peso_bioma.get(bioma, 1.0)

        score_focos = min(len(firms_df) / 100, 1.0)
        score_clima = min(df["temperature_max"].mean() / 40, 1.0) * max(1 - df["precipitation"].mean() / 50, 0)

        indice = round((score_focos * 0.6 + score_clima * 0.4) * peso * 10, 2)

        resumo = {
            "bioma": bioma,
            "total_focos": len(firms_df),
            "temp_media": round(df["temperature_max"].mean(), 1),
            "chuva_media": round(df["precipitation"].mean(), 1),
            "indice_risco": min(indice, 10.0)
        }

        return df, resumo