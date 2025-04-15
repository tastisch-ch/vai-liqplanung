import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from core.utils import chf_format
from core.parsing import parse_date_swiss_fallback
from logic.storage_buchungen import load_buchungen
from logic.storage_fixkosten import convert_fixkosten_to_buchungen
from logic.storage_simulation import convert_simulationen_to_buchungen
from logic.storage_mitarbeiter import convert_loehne_to_buchungen

def show():
    st.header("📊 Finanzplanung (Vorschau)")

    # Planungszeitraum und Filter-Optionen in der Sidebar
    st.sidebar.subheader("📆 Planungszeitraum")
    default_start = date.today()
    default_end = default_start + timedelta(days=270)  # Standard: 9 Monate
    
    start_date = st.sidebar.date_input("Startdatum", value=default_start)
    end_date = st.sidebar.date_input("Enddatum", value=default_end)
    
    # Weitere Filteroptionen
    st.sidebar.subheader("⚙️ Anzeigeoptionen")
    show_fixkosten = st.sidebar.checkbox("Fixkosten anzeigen", value=True)
    show_simulationen = st.sidebar.checkbox("Simulationen anzeigen", value=True)
    show_loehne = st.sidebar.checkbox("Lohnauszahlungen anzeigen", value=True)
    
    # Kategoriefilter
    st.sidebar.subheader("🔍 Suchen & Filtern")
    search_text = st.sidebar.text_input("Textsuche in Details", placeholder="Suchbegriff eingeben...")
    
    min_betrag = st.sidebar.number_input("Mindestbetrag (CHF)", value=0.0, step=100.0)
    max_betrag = st.sidebar.number_input("Maximalbetrag (CHF)", value=25000.0, step=1000.0)  # Erhöht für große Beträge
    
    # Sortieroptionen
    sort_options = ["Datum (aufsteigend)", "Datum (absteigend)", "Betrag (aufsteigend)", "Betrag (absteigend)"]
    sort_by = st.sidebar.selectbox("Sortieren nach", sort_options, index=0)
    
    # Exportoptionen
    st.sidebar.subheader("📊 Export")
    export_format = st.sidebar.selectbox("Exportformat", ["CSV", "Excel", "PDF"])
    if st.sidebar.button("Übersicht exportieren"):
        st.sidebar.success("Export-Funktion wird in einer zukünftigen Version implementiert.")
    
    # Daten laden und vorbereiten
    if "edited_df" in st.session_state:
        df = st.session_state.edited_df.copy()
    else:
        df = load_buchungen()

    # Überprüfe, ob df None oder leer ist, bevor du fortfährst
    if df is None or df.empty:
        st.info("Noch keine Daten verfügbar.")
        return

    df = df.copy()
    df.columns = df.columns.str.lower()
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["direction"] = df["direction"].str.lower()
    
    # Direkt nach Datum filtern für alle Buchungen
    df = df[df["date"].dt.date >= start_date]
    df = df[df["date"].dt.date <= end_date]
    
    # Speichere die Anzahl der ursprünglichen Buchungen für Info
    original_count = len(df)
    
    # Sortieren nach Datum (Standardsortierung)
    df = df.sort_values("date").reset_index(drop=True)

    # Wenn keine Kategorie-Spalte existiert, hinzufügen
    if "kategorie" not in df.columns:
        df["kategorie"] = "Standard"

    # Fixkosten laden, wenn aktiviert
    fixkosten_count = 0
    if show_fixkosten:
        try:
            # WICHTIG: Datum als pd.Timestamp übergeben, nicht als date
            fixkosten_df = convert_fixkosten_to_buchungen(
                pd.Timestamp(start_date), 
                pd.Timestamp(end_date)
            )
            
            if fixkosten_df is not None and not fixkosten_df.empty:
                # Spaltennamen vereinheitlichen
                fixkosten_df.columns = fixkosten_df.columns.str.lower()
                
                # Sicherstellen, dass date ein Timestamp ist
                if "date" in fixkosten_df.columns:
                    fixkosten_df["date"] = pd.to_datetime(fixkosten_df["date"], errors="coerce")
                
                if "kategorie" not in fixkosten_df.columns:
                    fixkosten_df["kategorie"] = "Fixkosten"
                
                fixkosten_count = len(fixkosten_df)
                
                # Kombinieren und sortieren
                combined_df = pd.concat([df, fixkosten_df], ignore_index=True)
                combined_df = combined_df.sort_values("date").reset_index(drop=True)
                
                df = combined_df
                st.success(f"✅ {fixkosten_count} Fixkosten in die Planung integriert")
        except Exception as e:
            st.error(f"❌ Fehler beim Laden der Fixkosten: {e}")
            st.exception(e)  # Debug-Info anzeigen
    
    # Simulationen laden, wenn aktiviert
    simulation_count = 0
    if show_simulationen:
        try:
            simulation_df = convert_simulationen_to_buchungen()
            
            if simulation_df is not None and not simulation_df.empty:
                # Datumsfilter auch auf Simulationen anwenden
                simulation_df["date"] = pd.to_datetime(simulation_df["date"], errors="coerce")
                simulation_df = simulation_df[simulation_df["date"].dt.date >= start_date]
                simulation_df = simulation_df[simulation_df["date"].dt.date <= end_date]
                
                # Spaltennamen normalisieren
                simulation_df.columns = simulation_df.columns.str.lower()
                
                # Sicherstellen, dass amount korrekt konvertiert wird
                simulation_df["amount"] = pd.to_numeric(simulation_df["amount"], errors="coerce")
                
                if "kategorie" not in simulation_df.columns:
                    simulation_df["kategorie"] = "Simulation"
                
                simulation_count = len(simulation_df)
                
                if simulation_count > 0:
                    combined_df = pd.concat([df, simulation_df], ignore_index=True)
                    combined_df = combined_df.sort_values("date").reset_index(drop=True)
                    
                    df = combined_df
                    st.success(f"✅ {simulation_count} Simulationen in die Planung integriert")
        except Exception as e:
            st.error(f"❌ Fehler beim Laden der Simulationen: {e}")
            st.exception(e)  # Debug-Info anzeigen
    
    # Lohndaten laden, wenn aktiviert
    lohn_count = 0
    if show_loehne:
        try:
            # WICHTIG: Datum als pd.Timestamp übergeben, nicht als date
            lohn_df = convert_loehne_to_buchungen(
                pd.Timestamp(start_date), 
                pd.Timestamp(end_date)
            )
            
            if lohn_df is not None and not lohn_df.empty:
                # Spaltennamen vereinheitlichen
                lohn_df.columns = lohn_df.columns.str.lower()
                
                # Sicherstellen, dass date ein Timestamp ist
                if "date" in lohn_df.columns:
                    lohn_df["date"] = pd.to_datetime(lohn_df["date"], errors="coerce")
                
                if "kategorie" not in lohn_df.columns:
                    lohn_df["kategorie"] = "Lohn"
                
                # KORREKTUR: Sicherstellen, dass keine "modified" Spalte existiert bei Lohnbuchungen
                if "modified" in lohn_df.columns:
                    lohn_df = lohn_df.drop(columns=["modified"])
                
                lohn_count = len(lohn_df)
                
                if lohn_count > 0:
                    combined_df = pd.concat([df, lohn_df], ignore_index=True)
                    combined_df = combined_df.sort_values("date").reset_index(drop=True)
                    
                    df = combined_df
                    st.success(f"✅ {lohn_count} Lohnbuchungen in die Planung integriert")
        except Exception as e:
            st.error(f"❌ Fehler beim Laden der Lohndaten: {e}")
            st.exception(e)  # Debug-Info anzeigen

    # KORRIGIERT: Beträge entsprechend der Richtung anpassen 
    # Wichtig: Ausgaben müssen als negative Werte für korrekte Kontostandsberechnung dargestellt werden
    df["amount"] = df.apply(
        lambda row: -abs(float(row["amount"])) if row["direction"].lower() == "outgoing" else abs(float(row["amount"])),
        axis=1
    )
    
    # Textsuche anwenden
    if search_text:
        # Sicherstellen, dass details eine Zeichenkette ist
        df["details"] = df["details"].astype(str)
        # Suche ohne Berücksichtigung der Groß-/Kleinschreibung
        df = df[df["details"].str.lower().str.contains(search_text.lower())]
    
    # Betragfilter anwenden
    df = df[(abs(df["amount"]) >= min_betrag) & (abs(df["amount"]) <= max_betrag)]
    
    # Sortierung anwenden
    if sort_by == "Datum (aufsteigend)":
        df = df.sort_values("date", ascending=True)
    elif sort_by == "Datum (absteigend)":
        df = df.sort_values("date", ascending=False)
    elif sort_by == "Betrag (aufsteigend)":
        df = df.sort_values("amount", ascending=True)
    elif sort_by == "Betrag (absteigend)":
        df = df.sort_values("amount", ascending=False)
    
    # Kontostand berechnen
    start_balance = st.session_state.get("start_balance", 0)
    
    # Zurück zu Datumsreihenfolge für die Kontostandsberechnung
    df = df.sort_values("date").reset_index(drop=True)
    
    # KORRIGIERT: Kontostandsberechnung - einfach kumulierte Summe der Beträge
    # Da wir bereits Ausgaben als negative Werte behandeln, funktioniert die cumsum-Funktion korrekt
    df["kontostand"] = start_balance + df["amount"].cumsum()

    # Hinweis für bearbeitete Einträge und Kategorien
    # Standardmäßig leere Hinweise setzen und nur setzen wenn modified=True
    df["hinweis"] = ""
    if "modified" in df.columns:
        df.loc[df["modified"] == True, "hinweis"] = "✏️"
    
    # Kategoriebasierte Hinweise
    df["hinweis"] = df.apply(
        lambda row: row["hinweis"] + " 📌" if row.get("kategorie") == "Fixkosten" else row["hinweis"],
        axis=1
    )
    
    # Simulationen mit 🔮 markieren
    df["hinweis"] = df.apply(
        lambda row: row["hinweis"] + " 🔮" if row.get("kategorie") == "Simulation" else row["hinweis"],
        axis=1
    )
    
    # Lohnauszahlungen mit 💰 markieren
    df["hinweis"] = df.apply(
        lambda row: row["hinweis"] + " 💰" if row.get("kategorie") == "Lohn" else row["hinweis"],
        axis=1
    )

    # Spalten für die Anzeige vorbereiten (ohne "direction")
    display_columns = ["date", "details", "amount", "kontostand", "hinweis"]
    
    # Füge Kategorie hinzu
    if "kategorie" in df.columns:
        display_columns.insert(4, "kategorie")
    
    # Sicherstellen, dass alle benötigten Spalten im DataFrame existieren
    for col in display_columns:
        if col not in df.columns:
            st.warning(f"Spalte '{col}' fehlt im DataFrame. Überprüfen Sie die Datenstruktur.")
            # Leere Spalte einfügen
            df[col] = ""
    
    # Wende die Sortierung erneut an (falls sie nicht Datum ist)
    if "aufsteigend" not in sort_by and "absteigend" not in sort_by:
        df = df.sort_values("date").reset_index(drop=True)
    
    display_df = df[display_columns].copy()
    display_df["date"] = display_df["date"].dt.strftime("%d.%m.%Y")
    display_df["amount"] = display_df["amount"].apply(chf_format)
    display_df["kontostand"] = display_df["kontostand"].apply(chf_format)

    # Spaltennamen übersetzen
    column_mapping = {
        "date": "Datum",
        "details": "Buchungsdetails",
        "amount": "Betrag",
        "kontostand": "Kontostand",
        "hinweis": "Hinweis",
        "kategorie": "Kategorie"
    }
    display_df = display_df.rename(columns=column_mapping)

    # Detaillierte Übersicht mit optimiertem Styling
    st.subheader("📝 Detaillierte Übersicht")
    
    # VEREINHEITLICHT: Farben basierend nur auf Einnahme/Ausgabe, unabhängig von der Kategorie
    def style_row(row):
        # Erstelle eine Liste mit Standard-Styling (kein Hintergrund)
        styles = [""] * len(row)
        
        # Hole den Index von row, um auf das Original-DataFrame zuzugreifen
        if row.name < len(df):
            # Wir nutzen amount für die Farbentscheidung (positiv = Einnahme, negativ = Ausgabe)
            amount_value = df.iloc[row.name]["amount"]
            
            # Einheitliche Farben: Grün für Einnahmen, Rot für Ausgaben, unabhängig von der Kategorie
            if amount_value > 0:
                # Grün für Einnahmen
                styles = ["background-color: #d1ffd6"] * len(row)
            else:
                # Rot für Ausgaben
                styles = ["background-color: #ffd6d6"] * len(row)
                
        return styles
    
    # Anzahl der Buchungen anzeigen
    filter_count = len(display_df)
    total_count = original_count + fixkosten_count + simulation_count + lohn_count
    
    if search_text or min_betrag > 0 or max_betrag < 25000:
        st.caption(f"Gefilterte Anzeige: {filter_count} von {total_count} Buchungen " +
                  f"(Zeitraum: {start_date.strftime('%d.%m.%Y')} bis {end_date.strftime('%d.%m.%Y')})")
    else:
        st.caption(f"Angezeigt werden {filter_count} Buchungen im Zeitraum {start_date.strftime('%d.%m.%Y')} bis {end_date.strftime('%d.%m.%Y')}")
    
    # Legende für die Icons
    legend_cols = st.columns(4)
    with legend_cols[0]:
        st.caption("📌 = Fixkosten")
    with legend_cols[1]:
        st.caption("🔮 = Simulation")
    with legend_cols[2]:
        st.caption("💰 = Lohn")
    with legend_cols[3]:
        st.caption("✏️ = Bearbeitet")
    
    try:
        # Anwenden des Stylings auf die gesamte Zeile
        st.dataframe(
            display_df.style.apply(style_row, axis=1),
            use_container_width=True,
            height=700  # Großzügige Höhe für viele Einträge
        )
    except Exception as e:
        st.error(f"Fehler bei der Tabellenanzeige: {e}")
        st.write("Anzeige der Daten ohne Styling:")
        st.dataframe(display_df, use_container_width=True, height=700)