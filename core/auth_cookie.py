import streamlit as st
import extra_streamlit_components as stx
from datetime import datetime, timedelta
import json
from core.storage import supabase

def get_cookie_manager():
    """
    Gibt den Cookie-Manager zurück, der für die persistente Speicherung von Anmeldeinformationen verwendet wird.
    """
    # Verwende den Cookie-Manager aus der Session, wenn er bereits initialisiert wurde
    if "cookie_manager" in st.session_state and st.session_state["cookie_manager"] is not None:
        return st.session_state["cookie_manager"]
    
    # Erstelle einen neuen Cookie-Manager (sollte eigentlich nicht aufgerufen werden)
    # da der Cookie-Manager in app.py initialisiert wird
    try:
        cookie_manager = stx.CookieManager(key="auth_cookies_instance")
        st.session_state["cookie_manager"] = cookie_manager
        return cookie_manager
    except Exception as e:
        print(f"Fehler beim Erstellen des Cookie-Managers: {e}")
        return None

def save_auth_to_cookie(user, session, stay_logged_in=False):
    """
    Speichert die Authentifizierungsinformationen in einem Cookie.
    
    Args:
        user: Der Benutzer aus Supabase
        session: Die Session aus Supabase
        stay_logged_in: Ob der Benutzer eingeloggt bleiben möchte
    """
    cookie_manager = get_cookie_manager()
    if cookie_manager is None:
        print("Cookie-Manager nicht verfügbar. Authentifizierungsdaten können nicht gespeichert werden.")
        return False
    
    # Bestimme die Ablaufzeit des Cookies basierend auf "stay_logged_in"
    expiry_days = 30 if stay_logged_in else 1  # 30 Tage oder 1 Tag
    
    # Erstelle ein Dictionary mit den wichtigsten Authentifizierungsinformationen
    auth_data = {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "user_id": user.id,
        "email": user.email,
        "stay_logged_in": stay_logged_in,
        "created_at": datetime.now().isoformat()
    }
    
    # Speichere das Dictionary als JSON-String im Cookie
    cookie_manager.set("auth_data", json.dumps(auth_data), expires_days=expiry_days)
    
    return True

def load_auth_from_cookie():
    """
    Lädt Authentifizierungsinformationen aus einem Cookie und stellt die Session wieder her.
    
    Returns:
        bool: True, wenn die Authentifizierung erfolgreich ist, sonst False
    """
    try:
        cookie_manager = get_cookie_manager()
        if cookie_manager is None:
            print("Cookie-Manager nicht verfügbar. Authentifizierungsdaten können nicht geladen werden.")
            return False
            
        auth_data_str = cookie_manager.get("auth_data")
        
        if not auth_data_str:
            return False
        
        # Parse den JSON-String
        auth_data = json.loads(auth_data_str)
        
        # Stelle die Session mit den gespeicherten Tokens wieder her
        session = {
            "access_token": auth_data["access_token"],
            "refresh_token": auth_data["refresh_token"]
        }
        
        response = supabase.auth.set_session(session)
        
        if response and response.user:
            # Session erfolgreich wiederhergestellt, aktualisiere die Session-State-Variablen
            st.session_state.user = response.user
            st.session_state.is_authenticated = True
            st.session_state.stay_logged_in = auth_data["stay_logged_in"]
            st.session_state.last_activity = datetime.now()
            
            # Aktualisierte Token im Cookie speichern
            save_auth_to_cookie(response.user, response.session, auth_data["stay_logged_in"])
            
            # Benutzerrolle überprüfen
            user_data = supabase.table('profiles').select('*').eq('id', response.user.id).execute()
            
            print(f"Cookie-Auth: Benutzerrolle überprüft: {user_data.data}")  # Debugging
            
            if user_data.data and user_data.data[0].get('role') == 'admin':
                st.session_state.is_admin = True
                print("Cookie-Auth: Admin-Status gesetzt")  # Debugging
            else:
                st.session_state.is_admin = False
            
            from core.auth import lade_benutzereinstellungen
            # Benutzereinstellungen laden
            lade_benutzereinstellungen(response.user.id)
            
            return True
    except Exception as e:
        print(f"Fehler beim Laden der Authentifizierungsdaten aus dem Cookie: {e}")
        # Bei Fehlern das Cookie löschen
        try:
            cookie_manager = get_cookie_manager()
            if cookie_manager:
                cookie_manager.delete("auth_data")
        except:
            pass
    
    return False

def clear_auth_cookie():
    """
    Löscht das Authentifizierungs-Cookie.
    """
    cookie_manager = get_cookie_manager()
    if cookie_manager:
        cookie_manager.delete("auth_data")