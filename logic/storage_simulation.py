import pandas as pd
import uuid
from datetime import datetime, date
from core.storage import supabase

def load_simulationen():
    """Lädt alle Simulationen aus der Datenbank."""
    try:
        response = supabase.table("simulationen").select("*").execute()
        data = response.data
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)
    except Exception as e:
        print(f"Fehler beim Laden der Simulationen: {e}")
        return pd.DataFrame()

def save_simulationen(simulationen_data):
    """Speichert die Simulationsdaten in der Datenbank.
    
    Args:
        simulationen_data: Liste von Dictionaries oder DataFrame
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
                if "kategorie" in item:
                    item_copy = item.copy()
                    del item_copy["kategorie"]
                    cleaned_list.append(item_copy)
                else:
                    cleaned_list.append(item)
                    
            supabase.table("simulationen").insert(cleaned_list).execute()
            
        return True
    except Exception as e:
        print(f"Fehler beim Speichern der Simulationen: {e}")
        return False

def update_simulation_by_id(id, data):
    """Aktualisiert eine bestimmte Simulation anhand der ID.
    
    Args:
        id: Die ID der zu aktualisierenden Simulation
        data: Dictionary mit den zu aktualisierenden Daten
    """
    try:
        # Sicherstellen, dass das Datum im richtigen Format ist
        if "date" in data and not isinstance(data["date"], str):
            data["date"] = data["date"].strftime("%Y-%m-%d")
            
        # Sicherstellen, dass der Betrag ein float ist
        if "amount" in data:
            data["amount"] = float(data["amount"])
        
        # Aktualisierung durchführen
        supabase.table("simulationen").update(data).eq("id", id).execute()
        return True
    except Exception as e:
        print(f"Fehler beim Aktualisieren der Simulation: {e}")
        return False

def delete_simulation_by_id(id):
    """Löscht eine Simulation anhand der ID."""
    try:
        supabase.table("simulationen").delete().eq("id", id).execute()
        return True
    except Exception as e:
        print(f"Fehler beim Löschen der Simulation: {e}")
        return False

def add_new_simulation(date, details, amount, direction):
    """Fügt eine neue Simulation hinzu."""
    try:
        # Neue ID generieren
        new_id = str(uuid.uuid4())
        
        # Daten für die neue Simulation vorbereiten
        data = {
            "id": new_id,
            "date": date if isinstance(date, str) else date.strftime("%Y-%m-%d"),
            "details": details,
            "amount": float(amount),
            "direction": direction
            # "kategorie" wird weggelassen, da es in der Datenbank nicht existiert
        }
        
        # Neue Simulation einfügen
        supabase.table("simulationen").insert(data).execute()
        return True
    except Exception as e:
        print(f"Fehler beim Hinzufügen der Simulation: {e}")
        return False

def convert_simulationen_to_buchungen():
    """Konvertiert alle Simulationen in buchungs-ähnliche Einträge für die Liquiditätsplanung."""
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