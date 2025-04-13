import pandas as pd
from datetime import datetime, date, timedelta
import uuid
from core.storage import supabase
from dateutil.relativedelta import relativedelta

def load_fixkosten():
    """Lädt alle Fixkosten aus der Datenbank."""
    response = supabase.table("fixkosten").select("*").execute()
    data = response.data
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data)

def update_fixkosten_row(row_data):
    """Aktualisiert oder erstellt einen Fixkosten-Eintrag."""
    try:
        row_id = row_data.get("id")
        data = {
            "name": row_data.get("name"),
            "betrag": float(row_data.get("betrag")),  # Sicherstellen, dass es ein Float ist
            "rhythmus": row_data.get("rhythmus"),
            "start": (row_data.get("start").strftime("%Y-%m-%d") 
                      if hasattr(row_data.get("start"), "strftime") 
                      else str(row_data.get("start"))),
            "enddatum": (row_data.get("enddatum").strftime("%Y-%m-%d") 
                         if row_data.get("enddatum") and hasattr(row_data.get("enddatum"), "strftime") 
                         else row_data.get("enddatum"))
        }
        
        print(f"Debugging - Rohdaten: {row_data}")
        print(f"Debugging - Vorbereitete Daten: {data}")
        
        try:
            # Wenn bereits ein Eintrag existiert, aktualisieren
            if row_id:
                print(f"Debugging - Aktualisiere Eintrag mit ID: {row_id}")
                
                # Überprüfe, ob der Eintrag existiert, bevor die Aktualisierung erfolgt
                existing_entry = supabase.table("fixkosten").select("*").eq("id", row_id).execute()
                
                if not existing_entry.data:
                    print(f"Warnung: Kein Eintrag gefunden mit ID {row_id}. Füge neuen Eintrag ein.")
                    data["id"] = row_id  # Stelle sicher, dass die ID beibehalten wird
                    response = supabase.table("fixkosten").insert(data).execute()
                else:
                    response = supabase.table("fixkosten").update(data).eq("id", row_id).execute()
            else:
                # Sonst neu erstellen
                data["id"] = str(uuid.uuid4())
                print(f"Debugging - Erstelle neuen Eintrag mit ID: {data['id']}")
                response = supabase.table("fixkosten").insert(data).execute()
            
            # Erweiterte Fehlersuche
            print(f"Debugging - Supabase Antwort:")
            print(f"  - Vollständige Antwort: {response}")
            print(f"  - Daten: {response.data}")
            
            # Überprüfen Sie explizit die Antwort
            if not response.data:
                print("Warnung: Keine Daten in der Antwort")
                raise Exception("Speichern nicht erfolgreich: Keine Daten in der Antwort")
            
            return response.data
        
        except Exception as supabase_error:
            print(f"Supabase-Fehler: {supabase_error}")
            raise
    
    except Exception as e:
        print(f"Fehler beim Speichern der Fixkosten: {e}")
        import traceback
        traceback.print_exc()
        raise    
    except Exception as e:
        print(f"Fehler beim Speichern der Fixkosten: {e}")
        import traceback
        traceback.print_exc()
        raise
def delete_fixkosten_row(row_id):
    """Löscht einen Fixkosten-Eintrag."""
    try:
        supabase.table("fixkosten").delete().eq("id", row_id).execute()
        return True
    except Exception:
        return False

def adjust_for_weekend(payment_date):
    """
    Passt das Zahlungsdatum an, wenn es auf ein Wochenende fällt.
    Zahlungen werden auf den vorherigen Werktag verschoben.
    
    Args:
        payment_date: Das zu prüfende Datum (datetime.date)
    
    Returns:
        Angepasstes Datum (datetime.date)
    """
    # Umwandeln in ein date-Objekt, falls notwendig
    if isinstance(payment_date, datetime):
        payment_date = payment_date.date()
    
    # Prüfen des Wochentags (0 = Montag, 6 = Sonntag)
    weekday = payment_date.weekday()
    
    # Wenn Samstag (5) oder Sonntag (6), verschiebe auf den Freitag
    if weekday == 5:  # Samstag -> Freitag
        return payment_date - timedelta(days=1)
    elif weekday == 6:  # Sonntag -> Freitag
        return payment_date - timedelta(days=2)
    
    # Für alle anderen Wochentage, behalte das Datum bei
    return payment_date

def convert_fixkosten_to_buchungen(start_date, end_date):
    """
    Konvertiert Fixkosten in Buchungen für den Liquiditätsplan.
    Bei Zahlungsterminen am Wochenende wird der vorherige Werktag verwendet.
    
    Args:
        start_date: Startdatum für die Generierung (datetime oder date)
        end_date: Enddatum für die Generierung (datetime oder date)
    
    Returns:
        DataFrame mit Buchungen im gleichen Format wie die buchungen-Tabelle
    """
    # Datum in Timestamp-Objekte umwandeln für konsistente Vergleiche
    start_date = pd.Timestamp(start_date)
    end_date = pd.Timestamp(end_date)
    
    # Fixkosten laden
    fixkosten_df = load_fixkosten()
    
    if fixkosten_df.empty:
        return pd.DataFrame()
    
    # Sicherstellen, dass Datumsfelder korrekt formatiert sind
    fixkosten_df["start"] = pd.to_datetime(fixkosten_df["start"], errors="coerce")
    fixkosten_df["enddatum"] = pd.to_datetime(fixkosten_df["enddatum"], errors="coerce")
    
    # Nur aktive Fixkosten berücksichtigen (kein Enddatum oder Enddatum > start_date)
    heute = pd.Timestamp(date.today())
    aktive_fixkosten = fixkosten_df[
        (fixkosten_df["enddatum"].isna()) | 
        (fixkosten_df["enddatum"] > start_date)
    ].copy()
    
    if aktive_fixkosten.empty:
        return pd.DataFrame()
    
    # Buchungen generieren
    buchungen = []
    
    for _, fixkosten in aktive_fixkosten.iterrows():
        # Bestimme das Startdatum für diese Fixkosten
        kosten_start = max(fixkosten["start"], start_date)
        
        # Bestimme das Enddatum für diese Fixkosten
        kosten_ende = fixkosten["enddatum"] if pd.notna(fixkosten["enddatum"]) else end_date
        kosten_ende = min(kosten_ende, end_date)
        
        # Intervall basierend auf dem Rhythmus bestimmen
        if fixkosten["rhythmus"] == "monatlich":
            interval = relativedelta(months=1)
            prefix = "Monatliche Fixkosten"
        elif fixkosten["rhythmus"] == "quartalsweise":
            interval = relativedelta(months=3)
            prefix = "Quartalsfixkosten"
        elif fixkosten["rhythmus"] == "halbjährlich":
            interval = relativedelta(months=6)
            prefix = "Halbjährliche Fixkosten"
        elif fixkosten["rhythmus"] == "jährlich":
            interval = relativedelta(years=1)
            prefix = "Jährliche Fixkosten"
        else:
            continue  # Unbekannter Rhythmus
        
        # Buchungsdaten generieren
        current_date = kosten_start
        
        # Finde das erste Datum im zukünftigen Rhythmus
        while current_date <= kosten_ende:
            # Nur Buchungen für Daten nach dem Startdatum der Fixkosten
            if current_date >= fixkosten["start"]:
                # Nur Buchungen erstellen, die im angegebenen Zeitraum liegen
                if current_date <= kosten_ende:
                    # Hier passen wir das Zahlungsdatum an, wenn es auf ein Wochenende fällt
                    payment_date = adjust_for_weekend(current_date)
                    
                    # Speichere sowohl das geplante als auch das tatsächliche Zahlungsdatum
                    # für zukünftige Berechnungen (um den Rhythmus beizubehalten)
                    buchung = {
                        "id": str(uuid.uuid4()),
                        "date": pd.Timestamp(payment_date),  # Tatsächliches Zahlungsdatum (werktags)
                        "original_date": pd.Timestamp(current_date),  # Ursprüngliches Datum für den Rhythmus
                        "details": f"{prefix}: {fixkosten['name']}",
                        "amount": fixkosten["betrag"],
                        "direction": "Outgoing",
                        "modified": False,
                        "fixkosten_id": fixkosten["id"],  # Referenz zur ursprünglichen Fixkosten
                        "kategorie": "Fixkosten"
                    }
                    buchungen.append(buchung)
            
            # Zum nächsten Datum im Rhythmus wechseln
            # Wichtig: Verwende das ursprüngliche Datum für den Rhythmus, nicht das angepasste
            current_date += interval
    
    if not buchungen:
        return pd.DataFrame()
    
    # Entferne zusätzliche Spalte "original_date", damit das DataFrame kompatibel bleibt
    df = pd.DataFrame(buchungen)
    if "original_date" in df.columns:
        df = df.drop(columns=["original_date"])
    
    return df