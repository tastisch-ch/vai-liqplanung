from core.storage import supabase
import pandas as pd
import uuid
from datetime import datetime, date, timedelta

def load_mitarbeiter(user_id=None):
    """
    Lädt alle Mitarbeiter mit ihren Lohndaten aus der Datenbank.
    
    Args:
        user_id (str, optional): Benutzer-ID (wird nur für Audit-Trails verwendet, nicht zum Filtern)
        
    Returns:
        list: Liste der Mitarbeiter mit ihren Lohndaten
    """
    try:
        # Mitarbeiter laden - nicht nach Benutzer filtern
        mitarbeiter_response = supabase.table("mitarbeiter").select("*").execute()
        mitarbeiter_raw = mitarbeiter_response.data
        
        if not mitarbeiter_raw:
            return []
        
        # Löhne separat laden
        loehne_response = supabase.table("loehne").select("*").execute()
        loehne_raw = loehne_response.data
        
        # Mitarbeiter-Daten in ein Dictionary umwandeln
        mitarbeiter_dict = {m["id"]: {"id": m["id"], "Name": m["name"], "Lohn": []} for m in mitarbeiter_raw}
        
        # Löhne den entsprechenden Mitarbeitern zuordnen
        for lohn in loehne_raw:
            mitarbeiter_id = lohn.get("mitarbeiter_id")
            if mitarbeiter_id in mitarbeiter_dict:
                # Lohndaten vorbereiten
                lohn_data = {
                    "Start": lohn.get("start").split("T")[0] if isinstance(lohn.get("start"), str) else lohn.get("start"),
                    "Ende": lohn.get("ende").split("T")[0] if isinstance(lohn.get("ende"), str) and lohn.get("ende") else None,
                    "Betrag": float(lohn.get("betrag", 0))
                }
                mitarbeiter_dict[mitarbeiter_id]["Lohn"].append(lohn_data)
        
        # Als Liste zurückgeben
        return list(mitarbeiter_dict.values())
    except Exception as e:
        print(f"Fehler beim Laden der Mitarbeiter: {e}")
        return []

def save_mitarbeiter(mitarbeiter_list, user_id=None):
    """
    Speichert Mitarbeiter und ihre Lohndaten in der Datenbank.
    Verwendet die korrekte Datenbankstruktur mit separaten Tabellen.
    
    Args:
        mitarbeiter_list: Liste der Mitarbeiter
        user_id (str, optional): Benutzer-ID für Audit-Trails
        
    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    try:
        # Bestehende Mitarbeiter und Löhne laden, um Aktualisierungen zu verfolgen
        existing_mitarbeiter_response = supabase.table("mitarbeiter").select("id").execute()
        existing_mitarbeiter_ids = [m["id"] for m in existing_mitarbeiter_response.data]
        
        # Bestehende Lohndaten laden
        existing_loehne_response = supabase.table("loehne").select("id,mitarbeiter_id").execute()
        existing_loehne = existing_loehne_response.data
        
        # Datenstrukturen für Aktualisierungen vorbereiten
        new_mitarbeiter = []
        update_mitarbeiter = []
        delete_mitarbeiter_ids = existing_mitarbeiter_ids.copy()
        
        new_loehne = []
        existing_loehne_by_mitarbeiter = {}
        
        # Gruppierung der bestehenden Löhne nach Mitarbeiter-ID
        for lohn in existing_loehne:
            mitarbeiter_id = lohn.get("mitarbeiter_id")
            if mitarbeiter_id not in existing_loehne_by_mitarbeiter:
                existing_loehne_by_mitarbeiter[mitarbeiter_id] = []
            existing_loehne_by_mitarbeiter[mitarbeiter_id].append(lohn)
        
        # Aktuelle Zeit für Zeitstempel
        now = datetime.utcnow().isoformat()
        
        # Mitarbeiter-Daten verarbeiten
        for mitarbeiter in mitarbeiter_list:
            mitarbeiter_id = mitarbeiter.get("id")
            
            # Mitarbeiter-Daten vorbereiten
            mitarbeiter_data = {
                "name": mitarbeiter.get("Name", "Unbekannt"),
                "updated_at": now
            }
            
            # Benutzer-ID für Audit-Trails hinzufügen
            if user_id:
                mitarbeiter_data["user_id"] = user_id
            
            # 1. Neuer Mitarbeiter oder Update
            if mitarbeiter_id and mitarbeiter_id in existing_mitarbeiter_ids:
                # Update vorhandener Mitarbeiter
                supabase.table("mitarbeiter").update(mitarbeiter_data).eq("id", mitarbeiter_id).execute()
                
                # Mitarbeiter nicht mehr löschen
                if mitarbeiter_id in delete_mitarbeiter_ids:
                    delete_mitarbeiter_ids.remove(mitarbeiter_id)
            else:
                # Neuer Mitarbeiter
                mitarbeiter_id = str(uuid.uuid4())
                mitarbeiter_data["id"] = mitarbeiter_id
                mitarbeiter_data["created_at"] = now
                supabase.table("mitarbeiter").insert(mitarbeiter_data).execute()
                # ID im ursprünglichen Objekt aktualisieren
                mitarbeiter["id"] = mitarbeiter_id
            
            # 2. Lohndaten verarbeiten
            # Zuerst alte Lohndaten löschen
            if mitarbeiter_id in existing_loehne_by_mitarbeiter:
                for lohn in existing_loehne_by_mitarbeiter[mitarbeiter_id]:
                    supabase.table("loehne").delete().eq("id", lohn.get("id")).execute()
            
            # Neue Lohndaten einfügen
            for lohn in mitarbeiter.get("Lohn", []):
                lohn_data = {
                    "id": str(uuid.uuid4()),
                    "mitarbeiter_id": mitarbeiter_id,
                    "betrag": float(lohn.get("Betrag", 0)),
                    "start": lohn.get("Start"),
                    "ende": lohn.get("Ende"),
                    "created_at": now,
                    "updated_at": now
                }
                
                # Benutzer-ID für Audit-Trails hinzufügen
                if user_id:
                    lohn_data["user_id"] = user_id
                    
                supabase.table("loehne").insert(lohn_data).execute()
        
        # 3. Nicht mehr vorhandene Mitarbeiter löschen
        for delete_id in delete_mitarbeiter_ids:
            # Zuerst alle zugehörigen Löhne löschen
            if delete_id in existing_loehne_by_mitarbeiter:
                for lohn in existing_loehne_by_mitarbeiter[delete_id]:
                    supabase.table("loehne").delete().eq("id", lohn.get("id")).execute()
            
            # Dann den Mitarbeiter löschen
            supabase.table("mitarbeiter").delete().eq("id", delete_id).execute()
        
        return True
    except Exception as e:
        print(f"Fehler beim Speichern der Mitarbeiter: {e}")
        return False

def add_mitarbeiter(name, lohn_daten, user_id=None, created_at=None, updated_at=None):
    """
    Fügt einen neuen Mitarbeiter hinzu.
    
    Args:
        name: Name des Mitarbeiters
        lohn_daten: Liste der Lohndaten
        user_id (str, optional): Benutzer-ID für Audit-Trails
        created_at (str, optional): Erstellungszeitstempel
        updated_at (str, optional): Aktualisierungszeitstempel
        
    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    try:
        # Aktuelle Zeit für Zeitstempel
        now = datetime.utcnow().isoformat()
        
        # Neuen Mitarbeiter erstellen
        mitarbeiter_id = str(uuid.uuid4())
        mitarbeiter_data = {
            "id": mitarbeiter_id,
            "name": name,
            "created_at": created_at or now,
            "updated_at": updated_at or now
        }
        
        # Benutzer-ID für Audit-Trail hinzufügen
        if user_id:
            mitarbeiter_data["user_id"] = user_id
        
        # Mitarbeiter in die Datenbank einfügen
        supabase.table("mitarbeiter").insert(mitarbeiter_data).execute()
        
        # Lohndaten hinzufügen
        for lohn in lohn_daten:
            lohn_data = {
                "id": str(uuid.uuid4()),
                "mitarbeiter_id": mitarbeiter_id,
                "betrag": float(lohn.get("Betrag", 0)),
                "start": lohn.get("Start"),
                "ende": lohn.get("Ende"),
                "created_at": created_at or now,
                "updated_at": updated_at or now
            }
            
            # Benutzer-ID für Audit-Trail hinzufügen
            if user_id:
                lohn_data["user_id"] = user_id
                
            supabase.table("loehne").insert(lohn_data).execute()
            
        return True
    except Exception as e:
        print(f"Fehler beim Hinzufügen des Mitarbeiters: {e}")
        return False

def update_mitarbeiter(mitarbeiter_id, updated_data, user_id=None):
    """
    Aktualisiert einen bestehenden Mitarbeiter anhand der ID.
    
    Args:
        mitarbeiter_id: ID des Mitarbeiters
        updated_data: Aktualisierte Daten
        user_id (str, optional): Benutzer-ID für Audit-Trails
        
    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    try:
        # Aktuelle Zeit für Zeitstempel
        now = datetime.utcnow().isoformat()
        
        # Name aktualisieren, falls vorhanden
        if "Name" in updated_data:
            mitarbeiter_data = {
                "name": updated_data["Name"],
                "updated_at": now
            }
            
            # Benutzer-ID für Audit-Trail hinzufügen
            if user_id:
                mitarbeiter_data["user_id"] = user_id
                
            supabase.table("mitarbeiter").update(mitarbeiter_data).eq("id", mitarbeiter_id).execute()
        
        # Lohndaten aktualisieren, falls vorhanden
        if "Lohn" in updated_data:
            # Bestehende Löhne für diesen Mitarbeiter löschen
            loehne_response = supabase.table("loehne").select("id").eq("mitarbeiter_id", mitarbeiter_id).execute()
            for lohn in loehne_response.data:
                supabase.table("loehne").delete().eq("id", lohn["id"]).execute()
            
            # Neue Lohndaten einfügen
            for lohn in updated_data["Lohn"]:
                lohn_data = {
                    "id": str(uuid.uuid4()),
                    "mitarbeiter_id": mitarbeiter_id,
                    "betrag": float(lohn.get("Betrag", 0)),
                    "start": lohn.get("Start"),
                    "ende": lohn.get("Ende"),
                    "created_at": now,
                    "updated_at": now
                }
                
                # Benutzer-ID für Audit-Trail hinzufügen
                if user_id:
                    lohn_data["user_id"] = user_id
                    
                supabase.table("loehne").insert(lohn_data).execute()
        
        return True
    except Exception as e:
        print(f"Fehler beim Aktualisieren des Mitarbeiters: {e}")
        return False

def delete_mitarbeiter(mitarbeiter_id, user_id=None):
    """
    Löscht einen Mitarbeiter anhand der ID.
    
    Args:
        mitarbeiter_id: ID des Mitarbeiters
        user_id (str, optional): Benutzer-ID für Audit-Trails
        
    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    try:
        # Hier könnte man einen Audit-Trail-Eintrag erstellen
        if user_id:
            # Audit-Trail-Eintrag erstellen
            pass
            
        # Zuerst alle Lohndaten des Mitarbeiters löschen
        loehne_response = supabase.table("loehne").select("id").eq("mitarbeiter_id", mitarbeiter_id).execute()
        for lohn in loehne_response.data:
            supabase.table("loehne").delete().eq("id", lohn["id"]).execute()
        
        # Dann den Mitarbeiter löschen
        supabase.table("mitarbeiter").delete().eq("id", mitarbeiter_id).execute()
        
        return True
    except Exception as e:
        print(f"Fehler beim Löschen des Mitarbeiters: {e}")
        return False

def add_lohn_to_mitarbeiter(mitarbeiter_id, lohn_daten, user_id=None):
    """
    Fügt einem bestehenden Mitarbeiter einen neuen Lohneintrag hinzu.
    
    Args:
        mitarbeiter_id: ID des Mitarbeiters
        lohn_daten: Lohndaten
        user_id (str, optional): Benutzer-ID für Audit-Trails
        
    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    try:
        # Aktuelle Zeit für Zeitstempel
        now = datetime.utcnow().isoformat()
        
        # Lohndaten hinzufügen
        lohn_data = {
            "id": str(uuid.uuid4()),
            "mitarbeiter_id": mitarbeiter_id,
            "betrag": float(lohn_daten.get("Betrag", 0)),
            "start": lohn_daten.get("Start"),
            "ende": lohn_daten.get("Ende"),
            "created_at": now,
            "updated_at": now
        }
        
        # Benutzer-ID für Audit-Trail hinzufügen
        if user_id:
            lohn_data["user_id"] = user_id
            
        supabase.table("loehne").insert(lohn_data).execute()
        
        return True
    except Exception as e:
        print(f"Fehler beim Hinzufügen des Lohneintrags: {e}")
        return False

def update_lohn(mitarbeiter_id, lohn_index, updated_lohn, user_id=None):
    """
    Aktualisiert einen bestimmten Lohneintrag eines Mitarbeiters.
    
    Args:
        mitarbeiter_id: ID des Mitarbeiters
        lohn_index: Index des Lohneintrags
        updated_lohn: Aktualisierte Lohndaten
        user_id (str, optional): Benutzer-ID für Audit-Trails
        
    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    try:
        # Aktuelle Zeit für Zeitstempel
        now = datetime.utcnow().isoformat()
        
        # Alle Löhne des Mitarbeiters laden
        loehne_response = supabase.table("loehne").select("*").eq("mitarbeiter_id", mitarbeiter_id).execute()
        loehne = loehne_response.data
        
        # Prüfen, ob der Index gültig ist
        if lohn_index < 0 or lohn_index >= len(loehne):
            return False
        
        # Lohn-ID ermitteln
        lohn_id = loehne[lohn_index]["id"]
        
        # Lohndaten aktualisieren
        lohn_data = {
            "betrag": float(updated_lohn.get("Betrag", 0)),
            "start": updated_lohn.get("Start"),
            "ende": updated_lohn.get("Ende"),
            "updated_at": now
        }
        
        # Benutzer-ID für Audit-Trail hinzufügen
        if user_id:
            lohn_data["user_id"] = user_id
            
        supabase.table("loehne").update(lohn_data).eq("id", lohn_id).execute()
        
        return True
    except Exception as e:
        print(f"Fehler beim Aktualisieren des Lohneintrags: {e}")
        return False

def delete_lohn(mitarbeiter_id, lohn_index, user_id=None):
    """
    Löscht einen bestimmten Lohneintrag eines Mitarbeiters.
    
    Args:
        mitarbeiter_id: ID des Mitarbeiters
        lohn_index: Index des Lohneintrags
        user_id (str, optional): Benutzer-ID für Audit-Trails
        
    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    try:
        # Hier könnte man einen Audit-Trail-Eintrag erstellen
        if user_id:
            # Audit-Trail-Eintrag erstellen
            pass
            
        # Alle Löhne des Mitarbeiters laden
        loehne_response = supabase.table("loehne").select("*").eq("mitarbeiter_id", mitarbeiter_id).execute()
        loehne = loehne_response.data
        
        # Prüfen, ob der Index gültig ist
        if lohn_index < 0 or lohn_index >= len(loehne):
            return False
        
        # Lohn-ID ermitteln
        lohn_id = loehne[lohn_index]["id"]
        
        # Lohneintrag löschen
        supabase.table("loehne").delete().eq("id", lohn_id).execute()
        
        return True
    except Exception as e:
        print(f"Fehler beim Löschen des Lohneintrags: {e}")
        return False

def get_aktuelle_loehne(user_id=None):
    """
    Gibt die aktuellen Löhne aller Mitarbeiter für die Liquiditätsplanung zurück.
    
    Args:
        user_id (str, optional): Benutzer-ID für Audit-Trails
        
    Returns:
        list: Liste der aktuellen Löhne
    """
    try:
        # Alle Mitarbeiter mit Lohndaten laden - nicht nach Benutzer filtern
        mitarbeiter_list = load_mitarbeiter()
        aktuelle_loehne = []
        
        heute = date.today()
        
        # Für jeden Mitarbeiter den aktuellen Lohn bestimmen
        for mitarbeiter in mitarbeiter_list:
            if "Lohn" in mitarbeiter and mitarbeiter["Lohn"]:
                # Löhne nach Startdatum sortieren (neueste zuerst)
                sorted_loehne = sorted(
                    mitarbeiter["Lohn"],
                    key=lambda x: datetime.strptime(x["Start"], "%Y-%m-%d").date() if isinstance(x["Start"], str) else x["Start"],
                    reverse=True
                )
                
                # Den aktuell gültigen Lohn suchen
                for lohn in sorted_loehne:
                    # Startdatum verarbeiten
                    if isinstance(lohn["Start"], str):
                        start_date = datetime.strptime(lohn["Start"], "%Y-%m-%d").date()
                    else:
                        start_date = lohn["Start"]
                    
                    # Enddatum verarbeiten (kann None sein)
                    ende_date = None
                    if lohn.get("Ende") and lohn.get("Ende") != "None":
                        if isinstance(lohn["Ende"], str):
                            ende_date = datetime.strptime(lohn["Ende"], "%Y-%m-%d").date()
                        else:
                            ende_date = lohn["Ende"]
                    
                    # Prüfen, ob der Lohn aktuell gültig ist
                    if start_date <= heute and (ende_date is None or ende_date >= heute):
                        aktuelle_loehne.append({
                            "Mitarbeiter": mitarbeiter["Name"],
                            "Betrag": lohn["Betrag"],
                            "Start": start_date,
                            "Ende": ende_date
                        })
                        break  # Nur den aktuellsten gültigen Lohn pro Mitarbeiter
        
        return aktuelle_loehne
    except Exception as e:
        print(f"Fehler beim Abrufen der aktuellen Löhne: {e}")
        return []

def convert_loehne_to_buchungen(start_date, end_date, user_id=None):
    """
    Konvertiert Lohndaten in Buchungen für die Liquiditätsplanung.
    Löhne werden am 25. jeden Monats ausgezahlt.
    
    Args:
        start_date: Anfangsdatum für die Planung
        end_date: Enddatum für die Planung
        user_id (str, optional): Benutzer-ID für Audit-Trails
        
    Returns:
        pd.DataFrame: DataFrame mit den Lohnbuchungen
    """
    try:
        # Aktuelle Löhne laden - nicht nach Benutzer filtern
        loehne = get_aktuelle_loehne()
        
        if not loehne:
            return pd.DataFrame()
            
        buchungen = []
        
        # Monatsweise durchgehen und Lohnbuchungen für den 25. erstellen
        current_date = pd.Timestamp(start_date).to_pydatetime().date()
        end_date_py = pd.Timestamp(end_date).to_pydatetime().date()
        
        while current_date <= end_date_py:
            # Nur für den 25. des Monats Löhne generieren
            if current_date.day == 25:
                for lohn in loehne:
                    start_date_lohn = lohn.get("Start")
                    ende_date_lohn = lohn.get("Ende")
                    
                    # Prüfen, ob Lohn zum aktuellen Datum gültig ist
                    if (start_date_lohn is None or start_date_lohn <= current_date) and \
                       (ende_date_lohn is None or ende_date_lohn >= current_date):
                        buchung = {
                            "date": pd.Timestamp(current_date),
                            "details": f"Lohn {lohn['Mitarbeiter']}",
                            "amount": -float(lohn["Betrag"]),  # Negativer Betrag für Ausgabe
                            "direction": "Outgoing",
                            "kategorie": "Lohn"
                        }
                        
                        # Benutzer-ID für Audit-Trail hinzufügen
                        if user_id:
                            buchung["user_id"] = user_id
                            
                        buchungen.append(buchung)
            
            # Zum nächsten Tag
            current_date += timedelta(days=1)
        
        # DataFrame erstellen
        if buchungen:
            return pd.DataFrame(buchungen)
        else:
            return pd.DataFrame()
            
    except Exception as e:
        print(f"Fehler beim Konvertieren der Löhne zu Buchungen: {e}")
        return pd.DataFrame()