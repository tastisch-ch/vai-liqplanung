from datetime import datetime
import pandas as pd
from core.storage import supabase

TABLE_NAME = "loehne"

def load_loehne():
    try:
        response = supabase.table(TABLE_NAME).select("*").execute()
        data = response.data or []
        df = pd.DataFrame(data)
        if not df.empty:
            df["start"] = pd.to_datetime(df["start"])
            df["ende"] = pd.to_datetime(df["ende"], errors="coerce")
            df["betrag"] = pd.to_numeric(df["betrag"], errors="coerce")
        return df
    except Exception as e:
        print("❌ Fehler beim Laden der Löhne:", e)
        return pd.DataFrame(columns=["id", "mitarbeiter_id", "start", "ende", "betrag"])

def add_lohn(mitarbeiter_id: int, start, betrag: float, ende=None):
    try:
        lohn = {
            "mitarbeiter_id": mitarbeiter_id,
            "start": pd.to_datetime(start).strftime("%Y-%m-%d"),
            "betrag": float(betrag),
        }
        if ende:
            lohn["ende"] = pd.to_datetime(ende).strftime("%Y-%m-%d")
        supabase.table(TABLE_NAME).insert(lohn).execute()
        return True
    except Exception as e:
        print("❌ Fehler beim Hinzufügen eines Lohns:", e)
        return False
