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
from core.auth import prüfe_session_gültigkeit, log_user_activity


def show():
    # Authentifizierungsprüfung
    if not prüfe_session_gültigkeit():
        st.warning("Bitte melden Sie sich an, um auf diesen Bereich zuzugreifen")
        st.stop()
    
    # Benutzer-ID für Audit-Protokollierung
    user_id = st.session_state.user.id
    
    st.header("🧪 Simulation")

    # Session-State für Aktualisierungen
    if "simulation_aktualisiert" not in st.session_state:
        st.session_state.simulation_aktualisiert = False
    
    if st.session_state.simulation_aktualisiert:
        st.session_state.simulation_aktualisiert = False
        st.rerun()

    # Simulationen laden (alle Simulationen ohne Benutzerfilterung)
    sim_df = load_simulationen()
    
    # Aktivität protokollieren
    log_user_activity("Simulationsseite aufgerufen", {
        "anzahl_simulationen": len(sim_df) if sim_df is not None and not sim_df.empty else 0
    })

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
    if st.button("💡 Simulation hinzufügen"):
        if not sim_detail:
            st.error("❌ Bitte gib eine Beschreibung ein.")
        elif not sim_amount_input:
            st.error("❌ Bitte gib einen Betrag ein.")
        else:
            try:
                # Lohnbetrag konvertieren
                sim_amount = float(sim_amount_input.replace("'", "").replace(",", "."))
                
                if sim_amount <= 0:
                    st.error("❌ Bitte gib einen Betrag größer als 0 ein.")
                else:
                    # Aktuelle Zeit für Zeitstempel
                    now = datetime.now().isoformat()
                    
                    # Neue Simulation hinzufügen mit Benutzer-ID
                    if add_new_simulation(
                        date=sim_date,
                        details=sim_detail,
                        amount=sim_amount,
                        direction=sim_direction,
                        user_id=user_id,
                        created_at=now,
                        updated_at=now
                    ):
                        # Aktivität protokollieren
                        log_user_activity("Simulation hinzugefügt", {
                            "beschreibung": sim_detail,
                            "betrag": sim_amount,
                            "richtung": sim_direction,
                            "datum": sim_date.isoformat()
                        })
                        
                        st.success("✅ Simulationseintrag hinzugefügt")
                        st.session_state.simulation_aktualisiert = True
                        st.rerun()
                    else:
                        st.error("❌ Fehler beim Hinzufügen der Simulation")
                        
                        # Fehler protokollieren
                        log_user_activity("Fehler beim Hinzufügen einer Simulation", {
                            "beschreibung": sim_detail,
                            "fehler": "Hinzufügen fehlgeschlagen"
                        })
            except (ValueError, TypeError) as e:
                st.error(f"❌ Bitte gib einen gültigen Betrag ein. Fehler: {str(e)}")

    # Trennlinie
    st.markdown("---")

    # Bestehende Simulationen anzeigen
    st.subheader("Bestehende Simulationen")
    
    # Überprüfen, ob Simulationen vorhanden sind
    if sim_df is None or sim_df.empty:
        st.info("Noch keine Simulationen vorhanden. Füge oben eine neue Simulation hinzu.")
    else:
        # Liste aller aktuellen Simulationen
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
                            # Originale Werte für Audit-Logs
                            original_values = {
                                "date": sim_date.isoformat(),
                                "details": sim_details,
                                "amount": sim_amount,
                                "direction": sim_direction
                            }
                            
                            # Aktualisierte Daten in ein Dictionary packen
                            updated_sim = {
                                "date": edit_date,
                                "details": edit_details.strip(),
                                "amount": float(edit_amount),
                                "direction": edit_direction,
                                "user_id": user_id,  # Benutzer-ID mitgeben
                                "updated_at": datetime.now().isoformat()  # Aktualisierungszeitstempel
                            }
                            
                            # Simulation aktualisieren über die Funktion
                            if update_simulation_by_id(sim_id, updated_sim):
                                # Aktivität protokollieren
                                log_user_activity("Simulation bearbeitet", {
                                    "id": sim_id,
                                    "original": original_values,
                                    "neu": {
                                        "date": edit_date.isoformat(),
                                        "details": edit_details.strip(),
                                        "amount": float(edit_amount),
                                        "direction": edit_direction
                                    }
                                })
                                
                                st.success("✅ Änderungen gespeichert")
                                st.session_state.simulation_aktualisiert = True
                                st.rerun()
                            else:
                                st.error("❌ Fehler beim Speichern")
                                
                                # Fehler protokollieren
                                log_user_activity("Fehler beim Bearbeiten einer Simulation", {
                                    "id": sim_id,
                                    "fehler": "Bearbeiten fehlgeschlagen"
                                })
                                
                        except Exception as e:
                            st.error(f"❌ Fehler beim Speichern: {e}")
                            
                            # Fehler protokollieren
                            log_user_activity("Fehler beim Bearbeiten einer Simulation", {
                                "id": sim_id,
                                "fehler": str(e)
                            })
                
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
                            if delete_simulation_by_id(sim_id, user_id=user_id):
                                # Aktivität protokollieren
                                log_user_activity("Simulation gelöscht", {
                                    "id": sim_id,
                                    "details": sim_details,
                                    "date": sim_date.isoformat()
                                })
                                
                                st.success("✅ Simulation gelöscht")
                                if f"confirm_delete_{sim_id}" in st.session_state:
                                    del st.session_state[f"confirm_delete_{sim_id}"]
                                st.session_state.simulation_aktualisiert = True
                                st.rerun()
                            else:
                                st.error("❌ Löschen fehlgeschlagen")
                                
                                # Fehler protokollieren
                                log_user_activity("Fehler beim Löschen einer Simulation", {
                                    "id": sim_id,
                                    "fehler": "Löschen fehlgeschlagen"
                                })
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
                    # Alle Simulationen löschen (ohne Benutzerfilterung)
                    if save_simulationen([]):
                        # Aktivität protokollieren
                        log_user_activity("Alle Simulationen gelöscht", {
                            "anzahl": len(sim_df)
                        })
                        
                        st.success("✅ Alle Simulationseinträge gelöscht")
                        st.session_state.simulation_aktualisiert = True
                        st.rerun()
                    else:
                        st.error("❌ Fehler beim Löschen aller Simulationen")
                        
                        # Fehler protokollieren
                        log_user_activity("Fehler beim Löschen aller Simulationen", {
                            "fehler": "Löschen fehlgeschlagen"
                        })
            with col2:
                if st.button("❌ Abbrechen", key="cancel_delete_all"):
                    st.info("Löschvorgang abgebrochen")