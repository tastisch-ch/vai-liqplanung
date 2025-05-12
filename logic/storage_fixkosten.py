import pandas as pd
from datetime import datetime, date, timedelta
import uuid
from core.storage import supabase
from dateutil.relativedelta import relativedelta
import json  # Add import for better debug logging

def load_fixkosten(user_id=None):
    """
    Lädt alle Fixkosten aus der Datenbank.
    
    Args:
        user_id (str, optional): Benutzer-ID (wird nur für Audit-Trails verwendet, nicht zum Filtern)
        
    Returns:
        pd.DataFrame: DataFrame mit allen Fixkosten
    """
    response = supabase.table("fixkosten").select("*").execute()
    data = response.data
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data)

def update_fixkosten_row(row_data, user_id=None):
    """Aktualisiert oder erstellt einen Fixkosten-Eintrag."""
    try:
        # Besseres Logging - Eingangsdaten protokollieren
        print(f"Fixkosten Daten zum Speichern erhalten: {str(row_data)}")
        
        row_id = row_data.get("id")
        
        # Sicherstellen, dass die Beträge korrekt als float konvertiert werden
        try:
            betrag = float(row_data.get("betrag"))
        except (ValueError, TypeError) as e:
            print(f"Fehler bei der Konvertierung des Betrags: {e}")
            print(f"Betrag-Wert: {row_data.get('betrag')}, Typ: {type(row_data.get('betrag'))}")
            # Fallback zu 0.0, wenn die Konvertierung fehlschlägt
            betrag = 0.0
        
        # Verbesserte Datums-Verarbeitung
        start_date = None
        if row_data.get("start"):
            if hasattr(row_data.get("start"), "strftime"):
                start_date = row_data.get("start").strftime("%Y-%m-%d")
            else:
                start_date = str(row_data.get("start"))
            print(f"Start-Datum verarbeitet: {start_date}")
        
        # Verbesserte Enddatum-Verarbeitung
        end_date = None
        if row_data.get("enddatum"):
            if hasattr(row_data.get("enddatum"), "strftime"):
                end_date = row_data.get("enddatum").strftime("%Y-%m-%d")
            else:
                end_date = str(row_data.get("enddatum"))
            print(f"End-Datum verarbeitet: {end_date}")
        
        data = {
            "name": row_data.get("name"),
            "betrag": betrag,
            "rhythmus": row_data.get("rhythmus"),
            "start": start_date,
            "enddatum": end_date
        }
        
        # Benutzer-ID für Audit-Trail hinzufügen
        if user_id:
            data["user_id"] = user_id
            
        # Zeitstempel für Erstellung/Aktualisierung
        now = datetime.utcnow().isoformat()
        
        try:
            # Detailliertes Logging vor dem Datenbankaufruf
            print(f"Bereite Datenbankoperation vor - ID: {row_id}")
            # Daten zum Logging vorbereiten (ohne json.dumps, da dies zu Fehlern führen kann)
            safe_data = data.copy()
            print(f"Zu speichernde Daten: {str(safe_data)}")
            
            # Wenn bereits ein Eintrag existiert, aktualisieren
            if row_id:
                # Überprüfe, ob der Eintrag existiert, bevor die Aktualisierung erfolgt
                existing_entry = supabase.table("fixkosten").select("*").eq("id", row_id).execute()
                
                if not existing_entry.data:
                    print(f"Warnung: Kein Eintrag gefunden mit ID {row_id}. Füge neuen Eintrag ein.")
                    data["id"] = row_id
                    data["created_at"] = now
                    data["updated_at"] = now
                    print("Führe INSERT-Operation aus...")
                    response = supabase.table("fixkosten").insert(data).execute()
                    print("INSERT abgeschlossen.")
                else:
                    data["updated_at"] = now
                    print("Führe UPDATE-Operation aus...")
                    response = supabase.table("fixkosten").update(data).eq("id", row_id).execute()
                    print("UPDATE abgeschlossen.")
            else:
                # Sonst neu erstellen
                data["id"] = str(uuid.uuid4())
                data["created_at"] = now
                data["updated_at"] = now
                print(f"Erstelle neuen Eintrag mit ID: {data['id']}")
                response = supabase.table("fixkosten").insert(data).execute()
                print("Neuer Eintrag erstellt.")
            
            # Erfolgreiches Update oder Insert
            print("Datenbankoperation erfolgreich abgeschlossen.")
            return response.data if response and hasattr(response, 'data') else True
        
        except Exception as supabase_error:
            print(f"Supabase-Fehler: {supabase_error}")
            # Detaillierten Fehler protokollieren
            import traceback
            print("Kompletter Stacktrace:")
            traceback.print_exc()
            raise
    
    except Exception as e:
        print(f"Fehler beim Speichern der Fixkosten: {e}")
        print(f"Typ des Fehlers: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return None

def delete_fixkosten_row(row_id, user_id=None):
    """
    Löscht einen Fixkosten-Eintrag.
    
    Args:
        row_id (str): ID des zu löschenden Eintrags
        user_id (str, optional): Benutzer-ID für Audit-Trails
        
    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    try:
        # Wenn wir einen Audit-Trail benötigen, könnten wir hier
        # zuerst die Löschaktion protokollieren, bevor wir den Eintrag löschen
        if user_id:
            # Hier könnte man einen Audit-Trail-Eintrag erstellen
            pass
        
        # Zuerst prüfen, ob der Eintrag existiert
        check = supabase.table("fixkosten").select("id").eq("id", row_id).execute()
        if not check.data:
            print(f"Warnung: Kein Eintrag mit ID {row_id} zum Löschen gefunden.")
            return False
            
        # Dann löschen
        try:
            response = supabase.table("fixkosten").delete().eq("id", row_id).execute()
            
            # Erfolg durch Prüfung, ob die Response vorhanden ist
            return True if response is not None else False
            
        except Exception as delete_error:
            print(f"Fehler beim Löschen: {delete_error}")
            return False
        
    except Exception as e:
        print(f"Fehler beim Löschen des Fixkosten-Eintrags: {e}")
        import traceback
        traceback.print_exc()
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

def convert_fixkosten_to_buchungen(start_date, end_date, user_id=None):
    """
    Konvertiert Fixkosten in Buchungen für den Liquiditätsplan.
    Bei Zahlungsterminen am Wochenende wird der vorherige Werktag verwendet.
    
    Args:
        start_date: Startdatum für die Generierung (datetime oder date)
        end_date: Enddatum für die Generierung (datetime oder date)
        user_id (str, optional): Benutzer-ID für Audit-Trails
    
    Returns:
        DataFrame mit Buchungen im gleichen Format wie die buchungen-Tabelle
    """
    try:
        # Datum in Timestamp-Objekte umwandeln für konsistente Vergleiche
        start_date = pd.Timestamp(start_date)
        end_date = pd.Timestamp(end_date)
        print(f"Konvertiere Fixkosten für Zeitraum: {start_date} bis {end_date}")
        
        # Fixkosten laden - nicht nach Benutzer filtern
        fixkosten_df = load_fixkosten()
        
        if fixkosten_df.empty:
            print("Keine Fixkosten gefunden.")
            return pd.DataFrame()
        
        # Sicherstellen, dass Datumsfelder korrekt formatiert sind
        try:
            fixkosten_df["start"] = pd.to_datetime(fixkosten_df["start"], errors="coerce")
            fixkosten_df["enddatum"] = pd.to_datetime(fixkosten_df["enddatum"], errors="coerce")
        except Exception as e:
            print(f"Fehler bei der Datumskonvertierung: {e}")
            import traceback
            traceback.print_exc()
        
        # Nur aktive Fixkosten berücksichtigen (kein Enddatum oder Enddatum > start_date)
        heute = pd.Timestamp(date.today())
        try:
            aktive_fixkosten = fixkosten_df[
                (fixkosten_df["enddatum"].isna()) | 
                (fixkosten_df["enddatum"] > start_date)
            ].copy()
            
            print(f"Aktive Fixkosten gefunden: {len(aktive_fixkosten)}")
        except Exception as filter_error:
            print(f"Fehler beim Filtern der aktiven Fixkosten: {filter_error}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
        
        if aktive_fixkosten.empty:
            print("Keine aktiven Fixkosten im angegebenen Zeitraum.")
            return pd.DataFrame()
        
        # Buchungen generieren
        buchungen = []
        
        for _, fixkosten in aktive_fixkosten.iterrows():
            try:
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
                    print(f"Unbekannter Rhythmus: {fixkosten['rhythmus']}")
                    continue  # Unbekannter Rhythmus
                
                # Buchungsdaten generieren
                current_date = kosten_start
                
                # Finde das erste Datum im zukünftigen Rhythmus
                while current_date <= kosten_ende:
                    # Nur Buchungen für Daten nach dem Startdatum der Fixkosten
                    if current_date >= fixkosten["start"]:
                        # Nur Buchungen erstellen, die im angegebenen Zeitraum liegen
                        if current_date <= kosten_ende:
                            try:
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
                                
                                # Benutzer-ID für Audit-Trail hinzufügen, wenn vorhanden
                                if user_id:
                                    buchung["user_id"] = user_id
                                elif "user_id" in fixkosten and fixkosten["user_id"]:
                                    buchung["user_id"] = fixkosten["user_id"]
                                    
                                buchungen.append(buchung)
                            except Exception as buchung_error:
                                print(f"Fehler beim Erstellen einer Buchung: {buchung_error}")
                                import traceback
                                traceback.print_exc()
                    
                    # Zum nächsten Datum im Rhythmus wechseln
                    # Wichtig: Verwende das ursprüngliche Datum für den Rhythmus, nicht das angepasste
                    current_date += interval
            except Exception as fixkosten_error:
                print(f"Fehler bei der Verarbeitung von Fixkosten {fixkosten.get('id')}: {fixkosten_error}")
                import traceback
                traceback.print_exc()
                continue  # Fahre mit der nächsten Fixkosten fort
        
        # Konvertieren zu DataFrame
        if buchungen:
            print(f"Insgesamt {len(buchungen)} Buchungen aus Fixkosten generiert.")
            df = pd.DataFrame(buchungen)
            
            # Entferne zusätzliche Spalte "original_date", damit das DataFrame kompatibel bleibt
            if "original_date" in df.columns:
                df = df.drop(columns=["original_date"])
                
            return df
        else:
            print("Keine Buchungen aus Fixkosten generiert.")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"Fehler bei der Konvertierung von Fixkosten zu Buchungen: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()