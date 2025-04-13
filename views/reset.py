import streamlit as st
from logic.reset_data import reset_all_data

def show():
    st.header("🔄 App zurücksetzen")

    st.warning("⚠️ Durch das Zurücksetzen werden alle Buchungen, Simulationen, Fixkosten und Mitarbeitenden aus der Datenbank gelöscht.")

    if st.button("🚨 Jetzt zurücksetzen"):
        try:
            reset_all_data()
            st.success("✅ App erfolgreich zurückgesetzt.")
        except Exception as e:
            st.error(f"❌ Fehler beim Zurücksetzen: {e}")
