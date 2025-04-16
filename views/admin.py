import streamlit as st
import pandas as pd
from datetime import datetime
import json

from core.auth import (
    initialisiere_auth_state, 
    prüfe_session_gültigkeit, 
    benutzer_auflisten, 
    benutzer_bearbeiten, 
    benutzer_loeschen, 
    registrieren,
    speichere_benutzereinstellungen,
    log_user_activity,
    test_admin_create_user_direct
)

def show():
    """
    Admin-Dashboard anzeigen
    """
    # Authentifizierungsstatus initialisieren
    initialisiere_auth_state()
    
    # Prüfen, ob die Session noch gültig ist
    if not prüfe_session_gültigkeit():
        st.warning("Bitte melden Sie sich an, um auf diesen Bereich zuzugreifen")
        st.stop()
        
    # Nur für Administratoren
    if not st.session_state.is_authenticated or not st.session_state.is_admin:
        st.error("Sie haben keine Berechtigung, auf diesen Bereich zuzugreifen")
        st.stop()
    
    # Admin-Dashboard anzeigen
    st.title("🛠️ Admin-Dashboard")
    
    # Statusmeldungen anzeigen (falls vorhanden)
    if st.session_state.auth_message:
        message_type = st.session_state.auth_message_type
        message = st.session_state.auth_message
        
        if message_type == "success":
            st.success(message)
        elif message_type == "error":
            st.error(message)
        elif message_type == "info":
            st.info(message)
        elif message_type == "warning":
            st.warning(message)
            
        # Nachricht zurücksetzen
        st.session_state.auth_message = None
        st.session_state.auth_message_type = None
    
    # Tabs für verschiedene Admin-Funktionen
    tab1, tab2, tab3 = st.tabs([
        "👥 Benutzerverwaltung", 
        "🎨 Design-Einstellungen", 
        "📊 Aktivitätslog"
    ])
    
    with tab1:
        benutzer_management()
        
    with tab2:
        design_einstellungen()
        
    with tab3:
        aktivitaetslog()

def benutzer_management():
    """
    Benutzerverwaltungsbereich
    """
    st.subheader("Benutzerverwaltung")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Benutzerliste anzeigen
        users = benutzer_auflisten()
        if users:
            # Benutzer-Dataframe erstellen
            df = pd.DataFrame(users)
            
            # Datum formatieren
            if 'created_at' in df.columns:
                df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%d.%m.%Y %H:%M')
                
            # Spalten umbenennen für bessere Lesbarkeit
            column_map = {
                'id': 'ID',
                'name': 'Name',
                'email': 'E-Mail',
                'role': 'Rolle',
                'created_at': 'Erstellt am'
            }
            
            df = df.rename(columns={k: v for k, v in column_map.items() if k in df.columns})
            
            # Benutzer anzeigen
            st.dataframe(df, use_container_width=True)
            
            # Benutzer zum Bearbeiten auswählen
            if 'selected_user_id' not in st.session_state:
                st.session_state.selected_user_id = None
            
            # Benutzer für Bearbeitung auswählen
            user_ids = [user['id'] for user in users]
            user_options = [f"{user.get('name', 'Unbenannt')} ({user.get('email', user['id'])})" for user in users]
            
            selected_user_index = st.selectbox(
                "Benutzer bearbeiten:",
                range(len(user_options)),
                format_func=lambda i: user_options[i]
            )
            
            st.session_state.selected_user_id = user_ids[selected_user_index]
            
            # Benutzer löschen
            if st.button("Ausgewählten Benutzer löschen", type="primary", use_container_width=True):
                if st.session_state.selected_user_id:
                    # Bestätigungsdialog
                    if 'delete_confirmation' not in st.session_state:
                        st.session_state.delete_confirmation = False
                        
                    st.warning(f"Sind Sie sicher, dass Sie diesen Benutzer löschen möchten? Diese Aktion kann nicht rückgängig gemacht werden.")
                    
                    confirm_col1, confirm_col2 = st.columns(2)
                    with confirm_col1:
                        if st.button("Ja, löschen", type="primary", use_container_width=True):
                            if benutzer_loeschen(st.session_state.selected_user_id):
                                log_user_activity("Benutzer gelöscht", {"user_id": st.session_state.selected_user_id})
                                st.rerun()
                    with confirm_col2:
                        if st.button("Abbrechen", use_container_width=True):
                            st.rerun()
        else:
            st.info("Keine Benutzer gefunden")
    
    with col2:
        
        if st.button("🚧 Test: Admin-User direkt erstellen"):
            test_admin_create_user_direct()

        # Benutzer bearbeiten, wenn einer ausgewählt ist
        if st.session_state.selected_user_id:
            selected_user = next((user for user in users if user['id'] == st.session_state.selected_user_id), None)
            
            if selected_user:
                st.subheader(f"Benutzer bearbeiten")
                
                with st.form(key="edit_user_form"):
                    name = st.text_input("Name", value=selected_user.get('name', ''))
                    email = st.text_input("E-Mail", value=selected_user.get('email', ''), disabled=True)
                    
                    role_options = ["user", "admin", "read_only"]
                    role = st.selectbox(
                        "Rolle",
                        role_options,
                        index=role_options.index(selected_user.get('role', 'user')) if selected_user.get('role') in role_options else 0
                    )
                    
                    update_button = st.form_submit_button("Aktualisieren", use_container_width=True)
                    
                    if update_button:
                        update_data = {
                            "name": name,
                            "role": role,
                            "updated_at": datetime.now().isoformat()
                        }
                        
                        if benutzer_bearbeiten(st.session_state.selected_user_id, update_data):
                            log_user_activity("Benutzer bearbeitet", {"user_id": st.session_state.selected_user_id})
                            st.rerun()
        
        # Neuen Benutzer hinzufügen
        st.markdown("---")
        st.subheader("Neuen Benutzer hinzufügen")
        
        with st.form(key="add_user_form"):
            new_name = st.text_input("Name")
            new_email = st.text_input("E-Mail")
            new_password = st.text_input("Passwort", type="password")
            new_role = st.selectbox("Rolle", ["user", "admin", "read_only"])
            
            submit_button = st.form_submit_button("Benutzer erstellen", use_container_width=True)
            
            if submit_button:
                st.write("📩 Registrierungsversuch startet...")
                st.write("Eingegebene Daten:", new_name, new_email, new_role)

                if not new_name or not new_email or not new_password:
                    st.error("❌ Bitte füllen Sie alle Felder aus.")
                else:
                    result = registrieren(new_email, new_password, new_name, new_role)

                    if result:
                        log_user_activity("Benutzer erstellt", {"email": new_email, "role": new_role})
                        st.success("✅ Benutzer erfolgreich erstellt.")
                        st.rerun()
                    else:
                        st.error("❌ Benutzer konnte nicht erstellt werden. Siehe Fehlermeldung oben.")


def design_einstellungen():
    """
    Design-Einstellungen für die App
    """
    st.subheader("Design-Einstellungen")
    
    # Aktuelle Einstellungen anzeigen
    current_settings = st.session_state.design_settings
    
    with st.form(key="design_settings_form"):
        primary_color = st.color_picker(
            "Primärfarbe",
            value=current_settings.get("primary_color", "#4A90E2")
        )
        
        secondary_color = st.color_picker(
            "Sekundärfarbe",
            value=current_settings.get("secondary_color", "#111")
        )
        
        background_color = st.color_picker(
            "Hintergrundfarbe",
            value=current_settings.get("background_color", "#FFFFFF")
        )
        
        # Weitere Designoptionen können hier hinzugefügt werden
        
        submit_button = st.form_submit_button("Design-Einstellungen speichern", use_container_width=True)
        
        if submit_button:
            new_settings = {
                "primary_color": primary_color,
                "secondary_color": secondary_color,
                "background_color": background_color
            }
            
            if speichere_benutzereinstellungen(new_settings):
                log_user_activity("Design-Einstellungen geändert")
                st.success("Design-Einstellungen wurden gespeichert")
                st.rerun()

def aktivitaetslog():
    """
    Aktivitätslog anzeigen
    """
    st.subheader("Benutzeraktivitäten")
    
    try:
        # Hier sollte eine Funktion zum Abrufen von Benutzeraktivitäten aus Supabase hinzugefügt werden
        # Beispiel-Implementation:
        from core.storage import supabase
        
        response = supabase.table('user_activities').select('*').order('created_at', desc=True).limit(100).execute()
        
        if response.data:
            # Aktivitäten in DataFrame umwandeln
            df = pd.DataFrame(response.data)
            
            # Details als JSON anzeigen, wenn vorhanden
            if 'details' in df.columns:
                df['details'] = df['details'].apply(lambda x: json.dumps(json.loads(x), ensure_ascii=False, indent=2) if x else "")
            
            # Datum formatieren
            if 'created_at' in df.columns:
                df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%d.%m.%Y %H:%M:%S')
            
            # Benutzer-IDs durch Namen ersetzen
            if 'user_id' in df.columns:
                users = benutzer_auflisten()
                user_dict = {user['id']: user.get('name', user.get('email', user['id'])) for user in users}
                df['user'] = df['user_id'].apply(lambda x: user_dict.get(x, x))
            
            # Spalten umbenennen
            column_map = {
                'created_at': 'Zeitpunkt',
                'user': 'Benutzer',
                'action': 'Aktion',
                'details': 'Details'
            }
            
            df = df.rename(columns={k: v for k, v in column_map.items() if k in df.columns})
            
            # Anzeige der Aktivitäten
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Keine Aktivitäten gefunden")
            
    except Exception as e:
        st.error(f"Fehler beim Laden der Aktivitäten: {str(e)}")