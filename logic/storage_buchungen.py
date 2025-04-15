import pandas as pd
from datetime import datetime
import uuid
from core.parsing import parse_date_swiss_fallback
from core.storage import supabase

BUCHUNGEN_TABLE = "buchungen"

def load_buchungen(user_id=None):
    """
    Lädt alle Buchungen aus der Datenbank.
    
    Args:
        user_id (str, optional): Benutzer-ID (wird nur für Audit-Trails verwendet, nicht zum Filtern)
        
    Returns:
        pd.DataFrame: DataFrame mit allen Buchungen
    """
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


def save_buchungen(df, user_id=None):
    """
    Speichert Buchungen in der Datenbank.
    
    Args:
        df (pd.DataFrame): DataFrame mit den zu speichernden Buchungen
        user_id (str, optional): Benutzer-ID für Audit-Trails
        
    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    try:
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

        # Jetzt fügen wir user_id hinzu, wenn sie bereitgestellt wurde
        if user_id:
            if "user_id" not in df.columns:
                df["user_id"] = user_id
            
        # Aktuelle Zeit für created_at und updated_at
        now = datetime.utcnow().isoformat()
        if "created_at" not in df.columns:
            df["created_at"] = now
        if "updated_at" not in df.columns:
            df["updated_at"] = now

        # Upsert in Supabase
        for _, row in df.iterrows():
            record = row.to_dict()
            supabase.table(BUCHUNGEN_TABLE).upsert(record).execute()
            
        return True
    except Exception as e:
        print(f"Fehler beim Speichern der Buchungen: {e}")
        return False


def update_buchung_by_id(id, date, details, amount, direction, user_id=None, updated_at=None):
    """
    Aktualisiert eine einzelne Buchung anhand ihrer ID.
    
    Args:
        id (str): ID der zu aktualisierenden Buchung
        date (str): Datum der Buchung
        details (str): Details der Buchung
        amount (float): Betrag der Buchung
        direction (str): Richtung der Buchung (Incoming/Outgoing)
        user_id (str, optional): Benutzer-ID für Audit-Trail
        updated_at (str, optional): Aktualisierungszeitstempel
        
    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    try:
        # Stelle sicher, dass date als ISO-String gespeichert wird
        if isinstance(date, (pd.Timestamp, datetime)):
            date = date.isoformat()
        else:
            try:
                date = pd.to_datetime(date).isoformat()
            except:
                date = None

        update_data = {
            "date": date,
            "details": details,
            "amount": float(amount) if amount is not None else None,
            "direction": direction,
            "modified": True,
            "updated_at": updated_at or datetime.utcnow().isoformat()
        }
        
        # Füge user_id für Audit-Trail hinzu, wenn bereitgestellt
        if user_id:
            update_data["user_id"] = user_id

        supabase.table("buchungen").update(update_data).eq("id", id).execute()
        return True
    except Exception as e:
        print(f"Fehler beim Aktualisieren der Buchung: {e}")
        return False