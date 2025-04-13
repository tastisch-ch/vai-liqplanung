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
        1. **E-Banking-Daten**: Kopiere die HTML-Tabelle aus deinem E-Banking und füge sie unten ein.
        2. **Rechnungsdaten** (optional): Lade Excel-Datei mit ausstehenden Rechnungen hoch.
        3. Klicke auf "Import starten".
        
        **Hinweis**: Der Kontostand kann jederzeit über die Seitenleiste verwaltet werden.
        """)

    # Import-Formular
    with st.form("import_form"):
        st.subheader("Daten importieren")
        
        html_input = st.text_area("HTML-Tabelle aus E-Banking einfügen:", height=300)
        uploaded_excel = st.file_uploader("📄 Rechnungsdaten (Excel)", type=[".xlsx"])
        
        # Submitbutton
        submitted = st.form_submit_button("🚀 Import starten")
    
    # Import-Verarbeitung (außerhalb des Formulars)
    if submitted:
        if html_input:
            with st.spinner("Importiere Daten..."):
                try:
                    df_import = parse_html_output(html_input)
                    df_import["Amount"] = pd.to_numeric(df_import["Amount"], errors="coerce")
                    df_import["Date"] = df_import["Date"].apply(parse_date_swiss_fallback)
                    df_import["Direction"] = df_import["Amount"].apply(lambda x: "Outgoing" if x < 0 else "Incoming")

                    # Überfällige Rechnungen auf morgen verschieben
                    today = datetime.now().date()
                    df_import["Date"] = df_import["Date"].apply(
                        lambda d: max(d.date(), today + timedelta(days=1)) 
                        if d.date() < today else d.date()
                    )
                    df_import["Date"] = pd.to_datetime(df_import["Date"])

                    # Excel ergänzen
                    if uploaded_excel:
                        df_excel = pd.read_excel(BytesIO(uploaded_excel.read()))
                        tomorrow = today + timedelta(days=1)

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
                        df_excel["Direction"] = "Incoming"

                        df_import = pd.concat([df_import, df_excel], ignore_index=True)

                    # ✅ Alle Buchungen laden
                    all_df = load_buchungen()
                    all_df["Date"] = pd.to_datetime(all_df["Date"])

                    if "modified" not in all_df.columns:
                        all_df["modified"] = False

                    modified_df = all_df[all_df["modified"] == True]
                    unmodified_df = all_df[all_df["modified"] == False]

                    # 🔍 Vergleichsfunktion mit Schutz gegen modifizierte Duplikate
                    def is_duplicate(row):
                        # Wenn die Buchung von einer bearbeiteten Buchung ersetzt wurde → nicht importieren
                        match_modified = modified_df[
                            (modified_df["Details"] == row["Details"]) &
                            (modified_df["Direction"] == row["Direction"]) &
                            (abs(modified_df["Amount"] - row["Amount"]) < 0.01)
                        ]
                        if not match_modified.empty:
                            return True  # wurde ersetzt

                        match_unmodified = unmodified_df[
                            (unmodified_df["Details"] == row["Details"]) &
                            (unmodified_df["Direction"] == row["Direction"]) &
                            (abs(unmodified_df["Amount"] - row["Amount"]) < 0.01)
                        ]
                        return not match_unmodified.empty

                    df_import["is_duplicate"] = df_import.apply(is_duplicate, axis=1)
                    df_new = df_import[df_import["is_duplicate"] == False].drop(columns=["is_duplicate"])

                    if df_new.empty:
                        st.info("ℹ️ Alle Buchungen sind bereits vorhanden oder wurden im Editor angepasst.")
                        return

                    df_new["id"] = [str(uuid.uuid4()) for _ in range(len(df_new))]
                    df_new["modified"] = False

                    save_buchungen(df_new)
                    
                    # Kontostand wird nicht mehr aus dem Import gesetzt - stattdessen Hinweis
                    st.success(f"✅ {len(df_new)} neue Buchungen importiert.")
                    st.info("Du kannst den Kontostand jederzeit in der Seitenleiste anpassen.")
                    
                    # Wechsel-Button zur Planung
                    if st.button("Zur Planung wechseln"):
                        st.session_state.active_tab = "Planung"
                        st.experimental_rerun()
                        
                except Exception as e:
                    st.error(f"❌ Fehler beim Import: {str(e)}")
                    st.exception(e)
        else:
            st.error("❌ Bitte füge HTML-Tabelle ein.")

    # Abschnitt für bestehende Daten
    st.markdown("---")
    
    # Aktuelle Daten anzeigen
    existing_data = load_buchungen()
    if existing_data is not None and not existing_data.empty:
        st.subheader("Vorhandene Daten")
        st.caption(f"Es sind bereits {len(existing_data)} Buchungen importiert.")
        
        with st.expander("Vorhandene Daten anzeigen"):
            st.dataframe(
                existing_data[["Date", "Details", "Amount", "Direction"]].sort_values("Date", ascending=False).head(10),
                use_container_width=True
            )
            
            if len(existing_data) > 10:
                st.caption(f"Es werden nur die neuesten 10 von {len(existing_data)} Buchungen angezeigt.")