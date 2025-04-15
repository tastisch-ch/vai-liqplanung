import pandas as pd
import uuid
from datetime import datetime, date
from core.storage import supabase

def load_simulationen(user_id=None):
    """
    Lädt alle Simulationen aus der Datenbank.
    
    Args:
        user_id (str, optional): Benutzer-ID (wird nur für Audit-Trails verwendet, nicht zum Filtern)
        
    Returns:
        pd.DataFrame: DataFrame mit allen Simulationen
    """
    try:
        response = supabase.table("simulationen").select("*").execute()
        data = response.data
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)
    except Exception as e:
        print(f"Fehler beim Laden der Simulationen: {e}")
        return pd.DataFrame()

def save_simulationen(simulationen_data, user_id=None):
    """
    Speichert die Simulationsdaten in der Datenbank.
    
    Args:
        simulationen_data: Liste von Dictionaries oder DataFrame
        user_id (str, optional): Benutzer-ID für Audit-Trails
        
    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    try:
        # Wenn das ein DataFrame ist, zu Dict konvertieren
        if isinstance(simulationen_data, pd.DataFrame):
            simulationen_list = simulationen_data.to_dict(orient="records")
        else:
            simulationen_list = simulationen_data
            
        # Alle bestehenden Simulationen löschen
        supabase.table("simulationen").delete().neq("id", "dummy").execute()
        
        # Wenn neue Simulationen vorhanden sind, einfügen
        if simulationen_list:
            # Kategorie-Spalte entfernen, falls vorhanden
            cleaned_list = []
            for item in simulationen_list:
                item_copy = item.copy()
                
                # Kategorie entfernen, falls vorhanden
                if "kategorie" in item_copy:
                    del item_copy["kategorie"]
                
                # Benutzer-ID hinzufügen, wenn vorhanden
                if user_id and "user_id" not in item_copy:
                    item_copy["user_id"] = user_id
                
                # Zeitstempel für Audit-Trail
                now = datetime.utcnow().isoformat()
                if "created_at" not in item_copy:
                    item_copy["created_at"] = now
                if "updated_at" not in item_copy:
                    item_copy["updated_at"] = now
                
                cleaned_list.append(item_copy)
                    
            supabase.table("simulationen").insert(cleaned_list).execute()
            
        return True
    except Exception as e:
        print(f"Fehler beim Speichern der Simulationen: {e}")
        return False

def update_simulation_by_id(id, data, user_id=None):
    """
    Aktualisiert eine bestimmte Simulation anhand der ID.
    
    Args:
        id: Die ID der zu aktualisierenden Simulation
        data: Dictionary mit den zu aktualisierenden Daten
        user_id (str, optional): Benutzer-ID für Audit-Trails
        
    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    try:
        update_data = data.copy()
        
        # Sicherstellen, dass das Datum im richtigen Format ist
        if "date" in update_data and not isinstance(update_data["date"], str):
            update_data["date"] = update_data["date"].strftime("%Y-%m-%d")
            
        # Sicherstellen, dass der Betrag ein float ist
        if "amount" in update_data:
            update_data["amount"] = float(update_data["amount"])
        
        # Benutzer-ID für Audit-Trail hinzufügen
        if user_id:
            update_data["user_id"] = user_id
            
        # Aktualisierungszeitstempel
        if "updated_at" not in update_data or not update_data["updated_at"]:
            update_data["updated_at"] = datetime.utcnow().isoformat()
        
        # Aktualisierung durchführen
        supabase.table("simulationen").update(update_data).eq("id", id).execute()
        return True
    except Exception as e:
        print(f"Fehler beim Aktualisieren der Simulation: {e}")
        return False

def delete_simulation_by_id(id, user_id=None):
    """
    Löscht eine Simulation anhand der ID.
    
    Args:
        id: Die ID der zu löschenden Simulation
        user_id (str, optional): Benutzer-ID für Audit-Trails
        
    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    try:
        # Hier könnte man einen Audit-Trail-Eintrag erstellen
        if user_id:
            # Audit-Trail-Eintrag für Löschung
            pass
            
        supabase.table("simulationen").delete().eq("id", id).execute()
        return True
    except Exception as e:
        print(f"Fehler beim Löschen der Simulation: {e}")
        return False

def add_new_simulation(date, details, amount, direction, user_id=None, created_at=None, updated_at=None):
    """
    Fügt eine neue Simulation hinzu.
    
    Args:
        date: Datum der Simulation
        details: Beschreibung der Simulation
        amount: Betrag der Simulation
        direction: Richtung der Simulation (Incoming/Outgoing)
        user_id (str, optional): Benutzer-ID für Audit-Trails
        created_at (str, optional): Erstellungszeitstempel
        updated_at (str, optional): Aktualisierungszeitstempel
        
    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    try:
        # Neue ID generieren
        new_id = str(uuid.uuid4())
        
        # Aktuelle Zeit für Zeitstempel
        now = datetime.utcnow().isoformat()
        
        # Daten für die neue Simulation vorbereiten
        data = {
            "id": new_id,
            "date": date if isinstance(date, str) else date.strftime("%Y-%m-%d"),
            "details": details,
            "amount": float(amount),
            "direction": direction,
            "created_at": created_at or now,
            "updated_at": updated_at or now
            # "kategorie" wird weggelassen, da es in der Datenbank nicht existiert
        }
        
        # Benutzer-ID für Audit-Trail hinzufügen
        if user_id:
            data["user_id"] = user_id
        
        # Neue Simulation einfügen
        supabase.table("simulationen").insert(data).execute()
        return True
    except Exception as e:
        print(f"Fehler beim Hinzufügen der Simulation: {e}")
        return False

def convert_simulationen_to_buchungen(user_id=None):
    """
    Konvertiert alle Simulationen in buchungs-ähnliche Einträge für die Liquiditätsplanung.
    
    Args:
        user_id (str, optional): Benutzer-ID für Audit-Trails
        
    Returns:
        pd.DataFrame: DataFrame mit buchungs-ähnlichen Einträgen
    """
    # Lade alle Simulationen (nicht nach Benutzer filtern)
    simulationen_df = load_simulationen()
    
    if simulationen_df.empty:
        return pd.DataFrame()
    
    # Kategorie-Spalte hinzufügen (nur für die Anzeige, nicht in der Datenbank)
    simulationen_df = simulationen_df.copy()
    simulationen_df["kategorie"] = "Simulation"
    
    # Datumsfeld korrekt formatieren (Groß-/Kleinschreibung anpassen)
    if "date" in simulationen_df.columns:
        simulationen_df["date"] = pd.to_datetime(simulationen_df["date"], errors="coerce")
    elif "Date" in simulationen_df.columns:
        simulationen_df["Date"] = pd.to_datetime(simulationen_df["Date"], errors="coerce")
    
    # Wichtig: Spaltennamen für die Konsistenz in Kleinbuchstaben konvertieren
    simulationen_df.columns = simulationen_df.columns.str.lower()
    
    return simulationen_df