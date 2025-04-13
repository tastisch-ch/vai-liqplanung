import pandas as pd
from datetime import datetime
import uuid
from core.parsing import parse_date_swiss_fallback
from core.storage import supabase

BUCHUNGEN_TABLE = "buchungen"

def load_buchungen():
    response = supabase.table(BUCHUNGEN_TABLE).select("*").execute()
    records = response.data if response.data else []
    if not records:
        return pd.DataFrame(columns=["id", "Date", "Details", "Amount", "Direction"])

    df = pd.DataFrame(records)

    # Einheitliche Großschreibung erzwingen für Kompatibilität im UI
    df = df.rename(columns={
        "date": "Date",
        "details": "Details",
        "amount": "Amount",
        "direction": "Direction"
    })

    # Konvertiere das Datum in das gewünschte Format (ISO-String: YYYY-MM-DD)
    df["Date"] = pd.to_datetime(df["Date"], format="%Y-%m-%d", errors="coerce")
    return df


def save_buchungen(df):
    df = df.copy()

    # Fehlende IDs erzeugen oder ergänzen
    if "id" not in df.columns:
        df["id"] = [str(uuid.uuid4()) for _ in range(len(df))]
    else:
        df["id"] = df["id"].apply(lambda x: x if pd.notna(x) and str(x).strip() != "" else str(uuid.uuid4()))

    # Spaltennamen klein schreiben für Supabase
    df.columns = [col.lower() for col in df.columns]

    # Datum in ISO-Format bringen
    if "date" in df.columns:
        def to_isoformat_safe(x):
            if isinstance(x, pd.Timestamp) or isinstance(x, datetime):
                return x.isoformat()
            try:
                return pd.to_datetime(x).isoformat()
            except:
                return None

        df["date"] = df["date"].apply(to_isoformat_safe)

    # ❌ Nicht benötigte Spalten entfernen
    df = df.drop(columns=[col for col in ["balance", "currency", "type"] if col in df.columns], errors="ignore")

    # Upsert in Supabase
    for _, row in df.iterrows():
        record = row.to_dict()
        supabase.table(BUCHUNGEN_TABLE).upsert(record).execute()


def update_buchung_by_id(id, date, details, amount, direction):
    # Stelle sicher, dass date als ISO-String gespeichert wird
    if isinstance(date, (pd.Timestamp, datetime)):
        date = date.isoformat()
    else:
        try:
            date = pd.to_datetime(date).isoformat()
        except:
            date = None

    supabase.table("buchungen").update({
        "date": date,
        "details": details,
        "amount": float(amount) if amount is not None else None,
        "direction": direction,
        "modified": True,
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", id).execute()

