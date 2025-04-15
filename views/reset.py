import streamlit as st
from logic.reset_data import reset_all_data
from core.auth import prüfe_session_gültigkeit, log_user_activity

def show():
    # Authentifizierungsprüfung
    if not prüfe_session_gültigkeit():
        st.warning("Bitte melden Sie sich an, um auf diesen Bereich zuzugreifen")
        st.stop()
        
    # Benutzer-ID für Datenbankabfragen verwenden
    user_id = st.session_state.user.id
    
    # Überprüfen, ob der Benutzer Admin-Rechte hat
    if not st.session_state.is_admin:
        st.error("Sie benötigen Administrator-Rechte, um alle Daten zurückzusetzen.")
        
        # Aktivität protokollieren
        log_user_activity("Unberechtigter Zugriff auf Reset-Funktion", {
            "benutzer_typ": "Nicht-Admin"
        })
        return
    
    st.header("🔄 App zurücksetzen")

    st.warning("⚠️ Durch das Zurücksetzen werden alle Buchungen, Simulationen, Fixkosten und Mitarbeitenden aus der Datenbank gelöscht.")
    
    # Bestätigungsfeld hinzufügen
    confirm_text = st.text_input("Bitte geben Sie 'ZURÜCKSETZEN' ein, um zu bestätigen:", "")
    
    if confirm_text == "ZURÜCKSETZEN":
        if st.button("🚨 Jetzt zurücksetzen"):
            try:
                # Datenlöschung nur für den angemeldeten Benutzer, wenn nicht Admin
                reset_all_data(user_id=user_id if not st.session_state.is_admin else None)
                
                # Aktivität protokollieren
                log_user_activity("App zurückgesetzt", {
                    "admin": st.session_state.is_admin,
                    "vollständiger_reset": st.session_state.is_admin
                })
                
                st.success("✅ App erfolgreich zurückgesetzt.")
            except Exception as e:
                st.error(f"❌ Fehler beim Zurücksetzen: {e}")
                
                # Fehler protokollieren
                log_user_activity("Fehler beim Zurücksetzen", {"fehler": str(e)})
    elif st.button("🚨 Jetzt zurücksetzen"):
        st.error("Bitte geben Sie 'ZURÜCKSETZEN' ein, um den Reset zu bestätigen.")
        
    # Aktivität protokollieren
    log_user_activity("Reset-Seite aufgerufen", {
        "admin": st.session_state.is_admin
    })