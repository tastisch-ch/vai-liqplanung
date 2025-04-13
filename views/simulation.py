import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from core.utils import chf_format
from logic.storage_simulation import (
    load_simulationen, 
    save_simulationen, 
    add_new_simulation,
    update_simulation_by_id,
    delete_simulation_by_id
)


def show():
    st.header("🧪 Simulation")

    # Session-State für Aktualisierungen
    if "simulation_aktualisiert" not in st.session_state:
        st.session_state.simulation_aktualisiert = False
    
    if st.session_state.simulation_aktualisiert:
        st.session_state.simulation_aktualisiert = False
        st.rerun()

    # Simulationen laden
    sim_df = load_simulationen()

    # Einführung
    with st.expander("ℹ️ Über Simulationen", expanded=False):
        st.markdown("""
        ### Was sind Simulationen?
        Simulationen sind hypothetische Einnahmen oder Ausgaben, die du für eine "Was-wäre-wenn"-Analyse hinzufügen kannst. 
        Sie werden in der Planungsansicht als 🔮 gekennzeichnet.

        **Beispiele für Simulationen:**
        - Potentielle neue Kunden
        - Mögliche Kosteneinsparungen
        - Geplante Investitionen
        - Alternative Szenarien
        """)
    
    # Neue Simulation hinzufügen - OHNE FORM-CONTAINER
    st.subheader("Neue Simulation erstellen")
    
    # Typ der Simulation (Einnahme oder Ausgabe)
    sim_direction = st.selectbox(
        "Typ", 
        ["Incoming", "Outgoing"], 
        format_func=lambda x: "Einnahme" if x == "Incoming" else "Ausgabe"
    )
    
    # Beschreibung
    sim_detail = st.text_input(
        "Beschreibung",
        placeholder="z.B. Potentieller Neukunde XYZ"
    )
    
    # Datum und Betrag in zwei Spalten
    col1, col2 = st.columns(2)
    
    with col1:
        # BETRAG - deutlich sichtbar mit klarer Beschriftung
        sim_amount_input = st.text_input(
            "Betrag (CHF)",
            placeholder="z.B. 1'500.00"
        )
    
    with col2:
        # DATUM - mit aktuellem Datum als Voreinstellung
        sim_date = st.date_input(
            "Datum",
            value=date.today()
        )
    
    # Submit-Button außerhalb des Formulars
    if st.button("💡 Simulation hinzufügen", use_container_width=True):
        # Fehlerprüfung für Beschreibung
        if not sim_detail:
            st.error("Bitte gib eine Beschreibung ein.")
        else:
            # Betrag parsen und prüfen
            try:
                sim_amount = float(sim_amount_input.replace("'", "").replace(",", "."))
                if sim_amount <= 0:
                    st.error("Bitte gib einen Betrag größer als 0 ein.")
                else:
                    # Neue Simulation hinzufügen
                    if add_new_simulation(
                        date=sim_date,
                        details=sim_detail,
                        amount=sim_amount,
                        direction=sim_direction
                    ):
                        st.success("✅ Simulationseintrag hinzugefügt")
                        st.session_state.simulation_aktualisiert = True
                        st.rerun()
                    else:
                        st.error("❌ Fehler beim Hinzufügen der Simulation")
            except (ValueError, TypeError):
                st.error("Bitte gib einen gültigen Betrag ein.")

    # Trennlinie
    st.markdown("---")

    # Bestehende Simulationen anzeigen
    st.subheader("Bestehende Simulationen")
    
    # Überprüfen, ob Simulationen vorhanden sind
    if sim_df.empty:
        st.info("Noch keine Simulationen vorhanden. Füge oben eine neue Simulation hinzu.")
    else:
        # Einzelne Simulationen in Expandern anzeigen, ähnlich wie bei Fixkosten
        for idx, row in sim_df.iterrows():
            # Details aus der Zeile extrahieren
            sim_id = str(row.get('id', idx))
            sim_date = pd.to_datetime(row.get('date', row.get('Date', ''))).date()
            sim_details = row.get('details', row.get('Details', ''))
            sim_amount = float(row.get('amount', row.get('Amount', 0)))
            sim_direction = row.get('direction', row.get('Direction', 'Incoming'))
            
            # Formatieren für den Expander-Titel
            direction_text = "Einnahme" if sim_direction == "Incoming" else "Ausgabe"
            expander_title = f"{sim_date.strftime('%d.%m.%Y')} - {sim_details} – {chf_format(abs(sim_amount))} ({direction_text})"
            
            with st.expander(expander_title, expanded=False):
                # Form für jede Simulation
                with st.form(key=f"form_{sim_id}"):
                    # Zeile 1: Typ und Beschreibung
                    col1, col2 = st.columns(2)
                    with col1:
                        edit_direction = st.selectbox(
                            "Typ", 
                            ["Incoming", "Outgoing"], 
                            index=0 if sim_direction == "Incoming" else 1,
                            format_func=lambda x: "Einnahme" if x == "Incoming" else "Ausgabe",
                            key=f"direction_{sim_id}"
                        )
                    with col2:
                        edit_details = st.text_input(
                            "Beschreibung", 
                            value=sim_details, 
                            key=f"details_{sim_id}"
                        )
                    
                    # Zeile 2: Datum und Betrag
                    col3, col4 = st.columns(2)
                    with col3:
                        edit_date = st.date_input(
                            "Datum", 
                            value=sim_date, 
                            key=f"date_{sim_id}"
                        )
                    with col4:
                        edit_amount = st.number_input(
                            "Betrag (CHF)", 
                            value=abs(sim_amount), 
                            min_value=0.01, 
                            format="%.2f", 
                            key=f"amount_{sim_id}"
                        )
                    
                    # Speichern-Button
                    if st.form_submit_button("💾 Änderungen speichern"):
                        try:
                            # Aktualisierte Daten in ein Dictionary packen
                            updated_sim = {
                                "date": edit_date,
                                "details": edit_details.strip(),
                                "amount": float(edit_amount),
                                "direction": edit_direction
                            }
                            
                            # Simulation aktualisieren über die Funktion
                            if update_simulation_by_id(sim_id, updated_sim):
                                st.success("✅ Änderungen gespeichert")
                                st.session_state.simulation_aktualisiert = True
                                st.rerun()
                            else:
                                st.error("❌ Fehler beim Speichern")
                                
                        except Exception as e:
                            st.error(f"❌ Fehler beim Speichern: {e}")
                
                # Löschen-Button außerhalb des Forms, ähnlich wie bei Fixkosten
                if st.button("🗑️ Simulation löschen", key=f"delete_{sim_id}"):
                    st.session_state[f"confirm_delete_{sim_id}"] = True
                    st.rerun()
                
                # Löschen bestätigen, wenn der Button geklickt wurde
                if st.session_state.get(f"confirm_delete_{sim_id}", False):
                    st.warning("⚠️ Willst du diesen Simulationseintrag wirklich löschen?")
                    confirm_col1, confirm_col2 = st.columns(2)
                    with confirm_col1:
                        if st.button("❌ Ja, löschen", key=f"confirm_yes_{sim_id}"):
                            if delete_simulation_by_id(sim_id):
                                st.success("✅ Simulation gelöscht")
                                if f"confirm_delete_{sim_id}" in st.session_state:
                                    del st.session_state[f"confirm_delete_{sim_id}"]
                                st.session_state.simulation_aktualisiert = True
                                st.rerun()
                            else:
                                st.error("❌ Löschen fehlgeschlagen")
                    with confirm_col2:
                        if st.button("Abbrechen", key=f"confirm_no_{sim_id}"):
                            if f"confirm_delete_{sim_id}" in st.session_state:
                                del st.session_state[f"confirm_delete_{sim_id}"]
                            st.rerun()
        
        # Option zum Löschen aller Simulationen
        st.markdown("---")
        if st.button("🗑️ Alle Simulationen löschen"):
            # Bestätigung abfragen
            st.warning("⚠️ Bist du sicher, dass du alle Simulationen löschen möchtest?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Ja, alle löschen", key="confirm_delete_all"):
                    save_simulationen([])
                    st.success("✅ Alle Simulationseinträge gelöscht")
                    st.session_state.simulation_aktualisiert = True
                    st.rerun()
            with col2:
                if st.button("❌ Abbrechen", key="cancel_delete_all"):
                    st.info("Löschvorgang abgebrochen")