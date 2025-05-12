import streamlit as st
import pandas as pd
import uuid
from datetime import datetime, date
from core.parsing import parse_date_swiss_fallback
from logic.storage_fixkosten import load_fixkosten, update_fixkosten_row, delete_fixkosten_row
from core.utils import chf_format
from core.auth import prüfe_session_gültigkeit, log_user_activity, is_read_only

def show():
    # Authentifizierungsprüfung
    if not prüfe_session_gültigkeit():
        st.warning("Bitte melden Sie sich an, um auf diesen Bereich zuzugreifen")
        st.stop()
    
    # Benutzer-ID für Audit-Protokollierung
    user_id = st.session_state.user.id
    
    # Prüfen, ob der Benutzer Schreibrechte hat
    readonly_mode = is_read_only()
    
    st.header("📃 Fixkosten verwalten")

    # Hinweis anzeigen, wenn im Lesemodus
    if readonly_mode:
        st.info("Sie befinden sich im Lesemodus. Änderungen sind nicht möglich.")

    # Session-State für die Filtereinstellungen und Aktualisierungen
    if "nur_aktive_fixkosten" not in st.session_state:
        st.session_state.nur_aktive_fixkosten = True
    if "fixkosten_aktualisiert" not in st.session_state:
        st.session_state.fixkosten_aktualisiert = False
    
    # Callback-Funktion für das Zurücksetzen der Eingabefelder
    def reset_input_fields():
        # Statt direkter Zuweisung, Schlüssel löschen
        if "neu_name" in st.session_state:
            del st.session_state["neu_name"]
        if "neu_betrag" in st.session_state:
            del st.session_state["neu_betrag"]
        if "neu_rhythmus" in st.session_state:
            del st.session_state["neu_rhythmus"]
        if "neu_start" in st.session_state:
            del st.session_state["neu_start"]
        if "neu_end" in st.session_state:
            del st.session_state["neu_end"]
    
    # Erfolgs-Callback: Eingabefelder zurücksetzen und andere Aktionen ausführen
    def on_success_add():
        reset_input_fields()
        st.session_state.fixkosten_aktualisiert = True
        st.success("✅ Fixkosten hinzugefügt")
        # Statt eines sofortigen Reruns hier eine kleine Verzögerung
        import time
        time.sleep(0.8)  # Erfolgsmeldung für 0.8 Sekunden anzeigen
        st.rerun()
    
    if st.session_state.fixkosten_aktualisiert:
        st.session_state.fixkosten_aktualisiert = False
        st.rerun()

    # ➕ Neue Fixkosten hinzufügen - im Lesemodus deaktiviert
    with st.form("fixkosten_form"):
        st.subheader("➕ Neue Fixkosten hinzufügen")
        col1, col2, col3 = st.columns(3)
        with col1:
            # Eingabe mit Key und Standardwert "" für leeres Feld
            if "neu_name" not in st.session_state:
                st.session_state.neu_name = ""
            name = st.text_input("Bezeichnung (neu)", key="neu_name", disabled=readonly_mode)
        with col2:
            # Eingabe mit Key und Standardwert 0.0 für leeres Feld
            if "neu_betrag" not in st.session_state:
                st.session_state.neu_betrag = 0.0
            betrag = st.number_input("Betrag (CHF)", min_value=0.0, step=100.0, format="%.2f", key="neu_betrag", disabled=readonly_mode)
        with col3:
            rhythmus = st.selectbox("Rhythmus", ["monatlich", "quartalsweise", "halbjährlich", "jährlich"], key="neu_rhythmus", disabled=readonly_mode)

        col4, col5 = st.columns(2)
        with col4:
            datum = st.date_input("Startdatum", value=date.today(), key="neu_start", disabled=readonly_mode)
        with col5:
            enddatum = st.date_input("Enddatum (optional)", value=None, key="neu_end", disabled=readonly_mode)
            
        submitted = st.form_submit_button("✅ Hinzufügen", disabled=readonly_mode)

        if submitted and not readonly_mode:  # Nur ausführen, wenn nicht im Lesemodus
            if not name.strip():
                st.error("❌ Bitte gib eine Bezeichnung ein.")
                
            elif betrag <= 0:
                st.error("❌ Bitte gib einen gültigen Betrag ein.")
                
            else:
                try:
                    new_entry = {
                        "id": str(uuid.uuid4()),
                        "name": name.strip(),
                        "betrag": float(betrag),
                        "rhythmus": rhythmus,
                        "start": datum,
                        "enddatum": enddatum if enddatum != datum else None,
                        "user_id": user_id  # Benutzer-ID für Audit-Trail
                    }
                    
                    # Validierung vor dem Speichern
                    if not (isinstance(datum, date) or isinstance(datum, datetime)):
                        st.error("❌ Startdatum hat ein ungültiges Format.")
                        return
                        
                    if enddatum and not (isinstance(enddatum, date) or isinstance(enddatum, datetime)):
                        st.error("❌ Enddatum hat ein ungültiges Format.")
                        return
                    
                    # Speichern mit besserer Fehlerbehandlung
                    result = update_fixkosten_row(new_entry)
                    
                    if result is None:
                        st.error("❌ Fehler beim Speichern in der Datenbank. Bitte prüfe die Logdatei.")
                        return
                    
                    # Nach erfolgreicher Erstellung die Erfolgs-Callback-Funktion aufrufen
                    on_success_add()
                    
                except Exception as e:
                    st.error(f"❌ Fehler beim Hinzufügen: {e}")
                    # Zusätzliche Debug-Informationen
                    print(f"Fehlerdetails beim Hinzufügen: {str(e)}")
                    import traceback
                    traceback.print_exc()

    st.markdown("---")

    # 📄 Bestehende Einträge anzeigen und filtern
    # Lade alle Fixkosten ohne Benutzerfilterung
    df = load_fixkosten()
    if df.empty:
        st.info("Noch keine Fixkosten erfasst.")
        return

    # Daten vorbereiten
    df["start"] = pd.to_datetime(df["start"], errors="coerce")
    df["enddatum"] = pd.to_datetime(df.get("enddatum", None), errors="coerce")
    
    # Filter-Optionen
    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        filter_rhythmus = st.multiselect(
            "Nach Rhythmus filtern:", 
            options=["monatlich", "quartalsweise", "halbjährlich", "jährlich"],
            default=[]
        )
    with col_filter2:
        # Verwende Callback-Funktion, um den Wert im Session-State zu aktualisieren
        def on_filter_change():
            st.session_state.nur_aktive_fixkosten = not st.session_state.nur_aktive_fixkosten
            
        aktiv_filter = st.checkbox(
            "Nur aktive Fixkosten anzeigen", 
            value=st.session_state.nur_aktive_fixkosten,
            key="aktiv_filter_checkbox",
            on_change=on_filter_change
        )
    
    # Daten filtern
    filtered_df = df.copy()
    
    if filter_rhythmus:
        filtered_df = filtered_df[filtered_df["rhythmus"].isin(filter_rhythmus)]
    
    # Aktiv-Filter anwenden
    if st.session_state.nur_aktive_fixkosten:
        heute = pd.Timestamp(date.today())
        aktive_df = filtered_df[(filtered_df["enddatum"].isna()) | (filtered_df["enddatum"] > heute)]
        
        # Info anzeigen, wie viele gefiltert wurden
        inactive_count = len(filtered_df) - len(aktive_df)
        if inactive_count > 0:
            st.info(f"{inactive_count} beendete Fixkosten werden nicht angezeigt. Deaktiviere den Filter, um alle zu sehen.")
        
        filtered_df = aktive_df
    
    # Nach Namen sortieren
    filtered_df = filtered_df.sort_values("name")
    
    # Gesamtkosten anzeigen
    st.subheader(f"Aktuelle monatliche Fixkosten: {chf_format(calculate_monthly_costs(df))}")

    # Bestehenden Einträge anzeigen
    for idx, row in filtered_df.iterrows():
        # Format für den Expander-Titel
        heute = pd.Timestamp(date.today())
        
        # Überprüfung, ob der Eintrag aktiv ist
        ist_aktiv = pd.isna(row["enddatum"]) or row["enddatum"] > heute
        
        if ist_aktiv:
            status = "aktiv"
        else:
            status = f"bis {row['enddatum'].strftime('%d.%m.%Y')}"
            
        expander_title = f"{row['name']} – {chf_format(row['betrag'])} ({row['rhythmus']}, {status})"
        row_id = str(row['id'])
        
        with st.expander(expander_title, expanded=False):
            # Form für jede Fixkosten-Zeile
            with st.form(key=f"form_{row_id}"):
                # 🔹 Zeile 1: Name, Betrag, Rhythmus
                col1, col2, col3 = st.columns(3)
                name = col1.text_input("Bezeichnung", row["name"], key=f"name_{row_id}", disabled=readonly_mode)
                betrag = col2.number_input("Betrag (CHF)", value=float(row["betrag"]), min_value=0.0, step=100.0, format="%.2f", key=f"betrag_{row_id}", disabled=readonly_mode)
                rhythmus = col3.selectbox(
                    "Rhythmus",
                    ["monatlich", "quartalsweise", "halbjährlich", "jährlich"],
                    index=["monatlich", "quartalsweise", "halbjährlich", "jährlich"].index(row["rhythmus"]),
                    key=f"rhythmus_{row_id}",
                    disabled=readonly_mode
                )

                # 🔹 Zeile 2: Start, Enddatum
                col4, col5 = st.columns(2)
                start = col4.date_input("Startdatum", value=row["start"].date(), key=f"start_{row_id}", disabled=readonly_mode)
                
                end_value = row["enddatum"].date() if pd.notna(row["enddatum"]) else None
                enddatum = col5.date_input("Enddatum (optional)", value=end_value, key=f"end_{row_id}", disabled=readonly_mode)
                
                # Buttons basierend auf dem Status anzeigen - im Lesemodus deaktiviert
                if ist_aktiv:  # Aktiver Eintrag
                    save_col, stop_col = st.columns(2)
                    with save_col:
                        submitted = st.form_submit_button("💾 Änderungen speichern", disabled=readonly_mode)
                    with stop_col:
                        stopped = st.form_submit_button("🛑 Fixkosten beenden", disabled=readonly_mode)
                    reaktivieren = False
                else:  # Beendeter Eintrag
                    save_col, reaktivieren_col = st.columns(2)
                    with save_col:
                        submitted = st.form_submit_button("💾 Änderungen speichern", disabled=readonly_mode)
                    with reaktivieren_col:
                        reaktivieren = st.form_submit_button("🔄 Fixkosten reaktivieren", disabled=readonly_mode)
                    stopped = False
                
                # Nur ausführen wenn Buttons gedrückt UND nicht im Lesemodus
                if (submitted or stopped or reaktivieren) and not readonly_mode:
                    try:
                        # Bestimme das Enddatum basierend auf der Aktion
                        if stopped:
                            end_date = date.today()
                        elif reaktivieren:
                            end_date = None  # Reaktivieren setzt das Enddatum auf None
                        else:
                            end_date = enddatum
                        
                        # Validierung vor dem Speichern
                        if not (isinstance(start, date) or isinstance(start, datetime)):
                            st.error("❌ Startdatum hat ein ungültiges Format.")
                            return
                            
                        if end_date and not (isinstance(end_date, date) or isinstance(end_date, datetime)):
                            st.error("❌ Enddatum hat ein ungültiges Format.")
                            return
                        
                        # Betrag sicherstellen
                        try:
                            betrag_float = float(betrag)
                        except (ValueError, TypeError):
                            st.error("❌ Betrag konnte nicht als Zahl interpretiert werden.")
                            return
                            
                        # Eintrag aktualisieren
                        changed_row = {
                            "id": row_id,
                            "name": name.strip(),
                            "betrag": betrag_float,
                            "rhythmus": rhythmus,
                            "start": start,
                            "enddatum": end_date,
                            "user_id": user_id  # Benutzer-ID beibehalten
                        }
                        
                        # Speichern mit besserer Fehlerbehandlung
                        result = update_fixkosten_row(changed_row)
                        
                        if result is None:
                            st.error("❌ Fehler beim Speichern in der Datenbank. Bitte prüfe die Logdatei.")
                            return
                        
                        # Erfolgsrückmeldung
                        if stopped:
                            st.success(f"✅ Fixkosten gestoppt per {date.today().strftime('%d.%m.%Y')}")
                            # Bei Beendigung den Filter deaktivieren, damit der Eintrag sichtbar bleibt
                            if st.session_state.nur_aktive_fixkosten:
                                st.session_state.nur_aktive_fixkosten = False
                                st.info("Der Filter 'Nur aktive Fixkosten anzeigen' wurde deaktiviert, damit du den beendeten Eintrag sehen kannst.")
                        elif reaktivieren:
                            st.success("✅ Fixkosten erfolgreich reaktiviert")
                        else:
                            st.success("✅ Änderungen gespeichert")
                        
                        # Kurze Verzögerung für die Erfolgsmeldung
                        import time
                        time.sleep(0.8)
                            
                        st.session_state.fixkosten_aktualisiert = True
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Fehler beim Speichern: {e}")
                        # Zusätzliche Debug-Informationen
                        print(f"Fehlerdetails beim Speichern: {str(e)}")
                        import traceback
                        traceback.print_exc()
            
            # Löschen-Button außerhalb des Forms - im Lesemodus deaktiviert
            if not readonly_mode:
                if st.button("🗑️ Fixkosten löschen", key=f"delete_{row_id}"):
                    st.session_state[f"confirm_delete_{row_id}"] = True
                    st.rerun()
                
                if st.session_state.get(f"confirm_delete_{row_id}", False):
                    st.warning("⚠️ Willst du diesen Fixkosten-Eintrag wirklich löschen?")
                    confirm_col1, confirm_col2 = st.columns(2)
                    with confirm_col1:
                        if st.button("❌ Ja, löschen", key=f"confirm_yes_{row_id}"):
                            if delete_fixkosten_row(row_id):
                                st.success("✅ Fixkosten gelöscht")
                                
                                # Kurze Verzögerung für die Erfolgsmeldung
                                import time
                                time.sleep(0.8)
                                
                                if f"confirm_delete_{row_id}" in st.session_state:
                                    del st.session_state[f"confirm_delete_{row_id}"]
                                st.session_state.fixkosten_aktualisiert = True
                                st.rerun()
                            else:
                                st.error("❌ Löschen fehlgeschlagen")
                    with confirm_col2:
                        if st.button("Abbrechen", key=f"confirm_no_{row_id}"):
                            if f"confirm_delete_{row_id}" in st.session_state:
                                del st.session_state[f"confirm_delete_{row_id}"]
                            st.rerun()
                
def calculate_monthly_costs(df):
    """Berechnet die aktuellen monatlichen Gesamtkosten aller aktiven Fixkosten."""
    total = 0.0
    heute = pd.Timestamp(date.today())
    
    for _, row in df.iterrows():
        if pd.isna(row["enddatum"]) or row["enddatum"] > heute:
            betrag = float(row["betrag"])
            
            # Betrag je nach Rhythmus umrechnen
            if row["rhythmus"] == "monatlich":
                total += betrag
            elif row["rhythmus"] == "quartalsweise":
                total += betrag / 3
            elif row["rhythmus"] == "halbjährlich":
                total += betrag / 6
            elif row["rhythmus"] == "jährlich":
                total += betrag / 12
    
    return total