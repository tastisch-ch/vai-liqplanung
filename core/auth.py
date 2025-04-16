import streamlit as st
import json
import time
from core.storage import supabase
from datetime import datetime, timedelta

# Importiere die Cookie-Auth-Funktionen 
# (stelle sicher, dass du die Datei auth_cookie.py erstellt hast)
try:
    from core.auth_cookie import save_auth_to_cookie, load_auth_from_cookie, clear_auth_cookie
except ImportError:
    # Fallback-Funktionen, falls die Cookie-Bibliothek nicht verfügbar ist
    def save_auth_to_cookie(user, session, stay_logged_in=False):
        return False
    
    def load_auth_from_cookie():
        return False
    
    def clear_auth_cookie():
        pass

# ----------------------------------
# 🔐 Authentifizierungsfunktionen
# ----------------------------------

def initialisiere_auth_state():
    """Initialisiert alle authentifizierungsbezogenen Session-State-Variablen."""
    if "user" not in st.session_state:
        st.session_state.user = None
    if "is_authenticated" not in st.session_state:
        st.session_state.is_authenticated = False
        # Versuche, eine gespeicherte Session aus dem Cookie wiederherzustellen
        if not st.session_state.is_authenticated:
            from core.auth_cookie import load_auth_from_cookie
            try:
                load_auth_from_cookie()
            except Exception as e:
                print(f"Fehler beim Wiederherstellen der Session: {e}")
    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False
    if "auth_message" not in st.session_state:
        st.session_state.auth_message = None
    if "auth_message_type" not in st.session_state:
        st.session_state.auth_message_type = None
    if "stay_logged_in" not in st.session_state:
        st.session_state.stay_logged_in = False
    if "last_activity" not in st.session_state:
        st.session_state.last_activity = datetime.now()
    if "design_settings" not in st.session_state:
        st.session_state.design_settings = {
            "primary_color": "#4A90E2",
            "secondary_color": "#111",
            "background_color": "#FFFFFF"
        }
def anmelden(email, password, stay_logged_in=False):
    """
    Benutzeranmeldung über Supabase
    """
    try:
        # Supabase-Anmeldung versuchen
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        
        # Wenn erfolgreich, Benutzerinformationen speichern
        if response.user:
            st.session_state.user = response.user
            st.session_state.is_authenticated = True
            st.session_state.stay_logged_in = stay_logged_in
            st.session_state.last_activity = datetime.now()
            
            # Speichere Authentifizierungsdaten in ein Cookie, wenn "angemeldet bleiben" aktiviert ist
            if stay_logged_in:
                try:
                    from core.auth_cookie import save_auth_to_cookie
                    save_auth_to_cookie(response.user, response.session, stay_logged_in)
                except Exception as e:
                    print(f"Fehler beim Speichern des Cookies: {e}")
            
            # Benutzerrolle überprüfen
            user_data = supabase.table('profiles').select('*').eq('id', response.user.id).execute()
            
            if user_data.data and user_data.data[0].get('role') == 'admin':
                st.session_state.is_admin = True
            else:
                st.session_state.is_admin = False
                
            st.session_state.auth_message = "Erfolgreich angemeldet!"
            st.session_state.auth_message_type = "success"
            
            # Benutzereinstellungen laden
            lade_benutzereinstellungen(response.user.id)
            
            return True
            
    except Exception as e:
        st.session_state.auth_message = f"Anmeldung fehlgeschlagen: {str(e)}"
        st.session_state.auth_message_type = "error"
        
    return False

def abmelden():
    """
    Benutzerabmeldung
    """
    try:
        supabase.auth.sign_out()
        st.session_state.user = None
        st.session_state.is_authenticated = False
        st.session_state.is_admin = False
        st.session_state.stay_logged_in = False
        
        # Lösche das Cookie
        try:
            from core.auth_cookie import clear_auth_cookie
            clear_auth_cookie()
        except Exception as e:
            print(f"Fehler beim Löschen des Cookies: {e}")
            
        st.session_state.auth_message = "Erfolgreich abgemeldet."
        st.session_state.auth_message_type = "info"
        
        # Standardeinstellungen wiederherstellen
        st.session_state.design_settings = {
            "primary_color": "#4A90E2",
            "secondary_color": "#111",
            "background_color": "#FFFFFF"
        }
        
    except Exception as e:
        st.session_state.auth_message = f"Abmeldung fehlgeschlagen: {str(e)}"
        st.session_state.auth_message_type = "error"

def magic_link_anmelden(email):
    """
    Sendet einen Magic Link zur angegebenen E-Mail-Adresse.
    
    Args:
        email (str): E-Mail-Adresse des Benutzers
        
    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    try:
        # Supabase Magic Link senden
        response = supabase.auth.sign_in_with_otp({
            "email": email
        })
        
        if response:
            st.session_state.auth_message = f"Ein Magic Link wurde an {email} gesendet. Bitte prüfe deine E-Mails."
            st.session_state.auth_message_type = "info"
            
            # Aktivität protokollieren (optional)
            try:
                log_user_activity("Magic Link angefordert", {"email": email})
            except:
                pass  # Fehler bei der Protokollierung ignorieren
                
            return True
    except Exception as e:
        st.session_state.auth_message = f"Fehler beim Senden des Magic Links: {str(e)}"
        st.session_state.auth_message_type = "error"
    
    return False

def is_read_only():
    """
    Überprüft, ob der aktuelle Benutzer nur Leserechte hat.
    
    Returns:
        bool: True, wenn der Benutzer read_only ist, sonst False
    """
    if not st.session_state.is_authenticated or not st.session_state.user:
        return False
    
    try:
        user_data = supabase.table('profiles').select('*').eq('id', st.session_state.user.id).execute()
        
        return user_data.data and user_data.data[0].get('role') == 'read_only'
    except Exception as e:
        print(f"Fehler bei der Überprüfung der Read-Only-Rechte: {e}")
        return False

def registrieren(email, password, name, role='user'):
    """
    Neuen Benutzer registrieren (nur für Admins)
    """
    if not st.session_state.is_admin:
        st.session_state.auth_message = "Nur Administratoren können neue Benutzer anlegen."
        st.session_state.auth_message_type = "error"
        return False
    
    try:
        # Neuen Benutzer erstellen
        response = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
        })
        
        if response.user:
            # Benutzerprofil erstellen
            profile_data = {
                "id": response.user.id,
                "name": name,
                "role": role,
                "created_at": datetime.now().isoformat()
            }
            
            supabase.table('profiles').insert(profile_data).execute()
            
            st.session_state.auth_message = f"Benutzer {email} erfolgreich erstellt."
            st.session_state.auth_message_type = "success"
            return True
            
    except Exception as e:
        st.session_state.auth_message = f"Benutzerregistrierung fehlgeschlagen: {str(e)}"
        st.session_state.auth_message_type = "error"
        
    return False

def benutzer_auflisten():
    """
    Liste aller Benutzer aus der profiles-Tabelle abrufen (nur für Admins)
    """
    if not st.session_state.is_admin:
        return []
        
    try:
        response = supabase.table('profiles').select('*').execute()
        return response.data
    except Exception as e:
        st.session_state.auth_message = f"Fehler beim Abrufen der Benutzerliste: {str(e)}"
        st.session_state.auth_message_type = "error"
        return []

def benutzer_bearbeiten(user_id, data):
    """
    Benutzerdaten aktualisieren (nur für Admins)
    """
    if not st.session_state.is_admin:
        st.session_state.auth_message = "Nur Administratoren können Benutzer bearbeiten."
        st.session_state.auth_message_type = "error"
        return False
        
    try:
        supabase.table('profiles').update(data).eq('id', user_id).execute()
        st.session_state.auth_message = "Benutzerdaten erfolgreich aktualisiert."
        st.session_state.auth_message_type = "success"
        return True
    except Exception as e:
        st.session_state.auth_message = f"Fehler beim Aktualisieren der Benutzerdaten: {str(e)}"
        st.session_state.auth_message_type = "error"
        return False

def benutzer_loeschen(user_id):
    """
    Benutzer löschen (nur für Admins)
    """
    if not st.session_state.is_admin:
        st.session_state.auth_message = "Nur Administratoren können Benutzer löschen."
        st.session_state.auth_message_type = "error"
        return False
        
    try:
        # Benutzer in Supabase Auth löschen
        supabase.auth.admin.delete_user(user_id)
        
        # Entsprechendes Profil löschen
        supabase.table('profiles').delete().eq('id', user_id).execute()
        
        st.session_state.auth_message = "Benutzer erfolgreich gelöscht."
        st.session_state.auth_message_type = "success"
        return True
    except Exception as e:
        st.session_state.auth_message = f"Fehler beim Löschen des Benutzers: {str(e)}"
        st.session_state.auth_message_type = "error"
        return False

def passwort_zuruecksetzen(email):
    """
    Passwort-Reset-Email senden
    """
    try:
        supabase.auth.reset_password_email(email)
        st.session_state.auth_message = f"Passwort-Reset-Email wurde an {email} gesendet."
        st.session_state.auth_message_type = "info"
        return True
    except Exception as e:
        st.session_state.auth_message = f"Fehler beim Senden der Passwort-Reset-Email: {str(e)}"
        st.session_state.auth_message_type = "error"
        return False

def speichere_benutzereinstellungen(design_settings):
    """
    Speichert die Designeinstellungen des Benutzers
    """
    if not st.session_state.is_authenticated or not st.session_state.user:
        return False
        
    try:
        user_id = st.session_state.user.id
        
        # Überprüfen, ob bereits Einstellungen existieren
        existing = supabase.table('user_settings').select('*').eq('user_id', user_id).execute()
        
        settings_data = {
            "user_id": user_id,
            "settings": json.dumps(design_settings),
            "updated_at": datetime.now().isoformat()
        }
        
        if existing.data:
            # Update bestehender Einstellungen
            supabase.table('user_settings').update(settings_data).eq('user_id', user_id).execute()
        else:
            # Neue Einstellungen anlegen
            settings_data["created_at"] = datetime.now().isoformat()
            supabase.table('user_settings').insert(settings_data).execute()
            
        # Session-State aktualisieren
        st.session_state.design_settings = design_settings
        return True
        
    except Exception as e:
        st.error(f"Fehler beim Speichern der Benutzereinstellungen: {str(e)}")
        return False

def lade_benutzereinstellungen(user_id):
    """
    Lädt die gespeicherten Designeinstellungen des Benutzers
    """
    try:
        response = supabase.table('user_settings').select('settings').eq('user_id', user_id).execute()
        
        if response.data and response.data[0].get('settings'):
            settings = json.loads(response.data[0]['settings'])
            st.session_state.design_settings = settings
            return settings
            
    except Exception as e:
        st.error(f"Fehler beim Laden der Benutzereinstellungen: {str(e)}")
        
    # Standardeinstellungen zurückgeben, wenn nichts gefunden wurde
    return st.session_state.design_settings

def prüfe_session_gültigkeit():
    """
    Überprüft, ob die aktuelle Session noch gültig ist
    """
    if not st.session_state.is_authenticated:
        # Wenn nicht authentifiziert, versuche eine gespeicherte Session aus dem Cookie wiederherzustellen
        try:
            from core.auth_cookie import load_auth_from_cookie
            if load_auth_from_cookie():
                return True
        except Exception as e:
            print(f"Fehler beim Laden der Session aus dem Cookie: {e}")
        return False
        
    # Wenn "Eingeloggt bleiben" nicht aktiviert ist, prüfe auf Inaktivität
    if not st.session_state.stay_logged_in:
        current_time = datetime.now()
        # Abmelden nach 30 Minuten Inaktivität
        if current_time - st.session_state.last_activity > timedelta(minutes=30):
            abmelden()
            st.session_state.auth_message = "Automatisch abgemeldet aufgrund von Inaktivität."
            st.session_state.auth_message_type = "info"
            return False
    
    # Session ist aktiv, Zeit aktualisieren
    st.session_state.last_activity = datetime.now()
    return True


def log_user_activity(activity_name, details=None):
    """Benutzeraktivität protokollieren, mit Fehlerbehandlung für Rekursionsprobleme"""
    try:
        # Wenn keine Session oder kein Benutzer existiert, einfach zurückkehren ohne Fehler
        if not hasattr(st, 'session_state') or not hasattr(st.session_state, 'user'):
            return False
            
        # Verhindere Datenbankfehler durch Rekursion
        import json
        from datetime import datetime
        from core.storage import supabase
        
        # Direkte Einfügung ohne RLS-Richtlinien zu aktivieren (umgeht die Rekursion)
        try:
            activity_data = {
                "user_id": st.session_state.user.id,
                "action": activity_name,
                "details": json.dumps(details) if details else None,
                "created_at": datetime.now().isoformat()
            }
            
            # INSERT mit rpc anstelle von direkter Tabelleneinfügung
            # Dies umgeht die RLS-Richtlinien, die die Rekursion verursachen
            supabase.rpc('insert_user_activity', {
                'user_id_param': activity_data["user_id"],
                'action_param': activity_data["action"],
                'details_param': activity_data["details"],
                'created_at_param': activity_data["created_at"]
            }).execute()
            
            return True
        except Exception as inner_e:
            # Stille Ausnahmebehandlung für Datenbankfehler
            print(f"Stille Fehlerbehandlung bei Benutzeraktivität: {str(inner_e)}")
            return False
            
    except Exception as e:
        # Allgemeine Ausnahmebehandlung
        print(f"Fehler beim Protokollieren der Benutzeraktivität: {str(e)}")
        return False