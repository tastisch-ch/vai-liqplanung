import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO
import uuid

from core.parsing import parse_date_swiss_fallback, parse_html_output
from core.utils import chf_format
from logic.storage_buchungen import save_buchungen, load_buchungen

def show():
    st.header("📂 Datenimport")

    # Info-Box über die Trennung von Kontostand und Import
    st.info("ℹ️ Der Start-Kontostand kann jetzt direkt über die Sidebar eingestellt werden, unabhängig vom Datenimport.")

    with st.expander("📋 Importanleitung", expanded=True):
        st.markdown("""
        ### So importierst du deine Finanzdaten:
        1. **E-Banking-Daten**: Kopiere die HTML-Tabelle aus deinem E-Banking und füge sie unten ein (für Ausgaben).
        2. **Rechnungsdaten** (optional): Lade Excel-Datei mit ausstehenden Rechnungen hoch (für Einnahmen).
        3. Klicke auf "Import starten".
        
        **Hinweis**: Der Kontostand kann jederzeit über die Seitenleiste verwaltet werden.
        """)

    # Import-Formular
    with st.form("import_form"):
        st.subheader("Daten importieren")
        
        html_input = st.text_area("HTML-Tabelle aus E-Banking einfügen (Ausgaben):", height=300)
        uploaded_excel = st.file_uploader("📄 Rechnungsdaten (Excel, Einnahmen)", type=[".xlsx"])
        
        # Submitbutton
        submitted = st.form_submit_button("🚀 Import starten")
    
    # Import-Verarbeitung (außerhalb des Formulars)
    if submitted:
        if html_input or uploaded_excel:
            with st.spinner("Importiere Daten..."):
                try:
                    new_entries = []
                    html_count = 0
                    excel_count = 0
                    
                    # HTML-Import verarbeiten (nur Ausgaben)
                    if html_input:
                        df_import = parse_html_output(html_input)
                        df_import["Amount"] = pd.to_numeric(df_import["Amount"], errors="coerce")
                        df_import["Date"] = df_import["Date"].apply(parse_date_swiss_fallback)
                        df_import["Direction"] = "Outgoing"  # Immer als Ausgaben markieren

                        # Überfällige Rechnungen auf morgen verschieben
                        today = datetime.now().date()
                        df_import["Date"] = df_import["Date"].apply(
                            lambda d: max(d.date(), today + timedelta(days=1)) 
                            if d.date() < today else d.date()
                        )
                        df_import["Date"] = pd.to_datetime(df_import["Date"])
                        
                        html_count = len(df_import)
                        if not df_import.empty:
                            new_entries.append(df_import)

                    # Excel-Import verarbeiten (nur Einnahmen)
                    if uploaded_excel:
                        df_excel = pd.read_excel(BytesIO(uploaded_excel.read()))
                        tomorrow = datetime.now().date() + timedelta(days=1)

                        def parse_excel_date(cell):
                            if isinstance(cell, (pd.Timestamp, datetime)):
                                return pd.to_datetime(cell)
                            if isinstance(cell, str):
                                for fmt in ["%d.%m.%Y", "%Y-%m-%d"]:
                                    try:
                                        return pd.to_datetime(cell, format=fmt)
                                    except:
                                        continue
                                return pd.to_datetime(cell, dayfirst=True, errors="coerce")
                            return pd.NaT

                        df_excel["Zahlbar bis"] = df_excel["Zahlbar bis"].apply(parse_excel_date)
                        df_excel.loc[df_excel["Zahlbar bis"] < pd.to_datetime("today"), "Zahlbar bis"] = pd.to_datetime(tomorrow)
                        df_excel["Details"] = df_excel["Kunde"] + " " + df_excel["Kundennummer"].astype(str)
                        df_excel.rename(columns={"Zahlbar bis": "Date", "Brutto": "Amount"}, inplace=True)
                        df_excel = df_excel[["Date", "Details", "Amount"]]
                        df_excel["Direction"] = "Incoming"  # Immer als Einnahmen markieren
                        
                        excel_count = len(df_excel)
                        if not df_excel.empty:
                            new_entries.append(df_excel)
                    
                    # Wenn Daten vorhanden sind, kombinieren und Duplikate entfernen
                    if new_entries:
                        df_combined = pd.concat(new_entries, ignore_index=True)
                        
                        # ✅ Alle Buchungen laden
                        all_df = load_buchungen()
                        
                        if all_df is not None and not all_df.empty:
                            all_df["Date"] = pd.to_datetime(all_df["Date"])

                            if "modified" not in all_df.columns:
                                all_df["modified"] = False

                            # 🔍 Verbesserte Vergleichsfunktion, die auch modifizierte Buchungen berücksichtigt
                            def is_duplicate(row):
                                # Prüfen auf Duplikate basierend auf Details und Direction
                                matches = all_df[
                                    (all_df["Details"] == row["Details"]) &
                                    (all_df["Direction"] == row["Direction"])
                                ]
                                
                                # Wenn ein Match gefunden wurde
                                if not matches.empty:
                                    # Wenn es exakte Duplikate gibt (auch beim Betrag)
                                    exact_matches = matches[abs(matches["Amount"] - row["Amount"]) < 0.01]
                                    if not exact_matches.empty:
                                        return True
                                    
                                    # Wenn es modifizierte Einträge gibt (wo der Betrag verändert wurde)
                                    modified_matches = matches[matches["modified"] == True]
                                    if not modified_matches.empty:
                                        return True
                                        
                                return False

                            df_combined["is_duplicate"] = df_combined.apply(is_duplicate, axis=1)
                            df_new = df_combined[df_combined["is_duplicate"] == False].drop(columns=["is_duplicate"])
                        else:
                            df_new = df_combined
                        
                        if df_new.empty:
                            st.info("ℹ️ Alle Buchungen sind bereits vorhanden oder wurden im Editor angepasst.")
                        else:
                            df_new["id"] = [str(uuid.uuid4()) for _ in range(len(df_new))]
                            df_new["modified"] = False
                            save_buchungen(df_new)
                            
                            # Erfolgs-Nachricht
                            if html_input and uploaded_excel:
                                html_neue = len(df_new[df_new["Direction"] == "Outgoing"])
                                excel_neue = len(df_new[df_new["Direction"] == "Incoming"])
                                st.success(f"✅ {html_neue} neue Ausgaben und {excel_neue} neue Einnahmen importiert.")
                            elif html_input:
                                st.success(f"✅ {len(df_new)} neue Ausgaben importiert.")
                            else:
                                st.success(f"✅ {len(df_new)} neue Einnahmen importiert.")
                            
                            st.info("Du kannst den Kontostand jederzeit in der Seitenleiste anpassen.")
                            
                            # Wechsel-Button zur Planung
                            if st.button("Zur Planung wechseln"):
                                st.session_state.active_tab = "Planung"
                                st.experimental_rerun()
                    else:
                        st.info("Es wurden keine neuen Daten zum Importieren gefunden.")
                        
                except Exception as e:
                    st.error(f"❌ Fehler beim Import: {str(e)}")
                    st.exception(e)
        else:
            st.error("❌ Bitte füge HTML-Tabelle ein oder lade eine Excel-Datei hoch.")

    # Abschnitt für bestehende Daten
    st.markdown("---")
    
    # Aktuelle Daten anzeigen
    existing_data = load_buchungen()
    if existing_data is not None and not existing_data.empty:
        st.subheader("Vorhandene Daten")
        st.caption(f"Es sind bereits {len(existing_data)} Buchungen importiert.")
        
        with st.expander("Vorhandene Daten anzeigen"):
            # Filter-Optionen für die Anzeige
            view_options = st.radio(
                "Anzeigen:",
                ["Alle Buchungen", "Nur Einnahmen", "Nur Ausgaben", "Nur modifizierte Buchungen"],
                horizontal=True
            )
            
            if view_options == "Nur Einnahmen":
                display_df = existing_data[existing_data["Direction"] == "Incoming"]
            elif view_options == "Nur Ausgaben":
                display_df = existing_data[existing_data["Direction"] == "Outgoing"]
            elif view_options == "Nur modifizierte Buchungen":
                display_df = existing_data[existing_data["modified"] == True]
            else:
                display_df = existing_data
            
            if not display_df.empty:
                st.dataframe(
                    display_df[["Date", "Details", "Amount", "Direction", "modified"]].sort_values("Date", ascending=False),
                    use_container_width=True
                )
                st.caption(f"Es werden {len(display_df)} von {len(existing_data)} Buchungen angezeigt.")
            else:
                st.info("Keine Daten in dieser Kategorie gefunden.")