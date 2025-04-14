import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from core.parsing import parse_date_swiss_fallback
from logic.storage_buchungen import load_buchungen, update_buchung_by_id
from core.utils import chf_format

def show():
    st.header("✏️ Finanzplanung (editierbar)")

    # Lade alle Buchungen
    df_all = load_buchungen()

    if df_all is None or df_all.empty:
        st.info("Noch keine Daten vorhanden. Bitte importiere zuerst Daten.")
        return

    # Sidebar für Filter und Optionen
    st.sidebar.subheader("📆 Zeitraum anzeigen")
    default_start = date.today() - timedelta(days=30)  # Standardmäßig letzten Monat anzeigen
    default_end = date.today() + timedelta(days=90)   # Standardmäßig nächste 3 Monate anzeigen
    
    start_date = st.sidebar.date_input("Von", value=default_start)
    end_date = st.sidebar.date_input("Bis", value=default_end)
    
    # Weitere Filteroptionen
    st.sidebar.subheader("⚙️ Optionen")
    zeige_bearbeitet = st.sidebar.checkbox("Nur bearbeitete Einträge zeigen", value=False)
    
    # Daten vorbereiten
    df_all.columns = df_all.columns.str.lower()
    df_all["amount"] = pd.to_numeric(df_all["amount"], errors="coerce")
    df_all["date"] = pd.to_datetime(df_all["date"], errors="coerce").dt.normalize()
    
    # Nach Datum filtern
    df_filtered = df_all[df_all["date"].dt.date >= start_date]
    df_filtered = df_filtered[df_filtered["date"].dt.date <= end_date]
    
    # Nach bearbeiteten Einträgen filtern, wenn ausgewählt
    if zeige_bearbeitet:
        if "modified" in df_filtered.columns:
            df_filtered = df_filtered[df_filtered["modified"] == True]
            if df_filtered.empty:
                st.info("Keine bearbeiteten Einträge im gewählten Zeitraum vorhanden.")
                return
    
    # Nach Datum sortieren
    df_filtered = df_filtered.sort_values("date").reset_index(drop=True)
    
    # Anzahl der angezeigten Einträge
    st.caption(f"Es werden {len(df_filtered)} von {len(df_all)} Buchungen angezeigt.")
    
    # Editable DataFrame vorbereiten
    editable_df = df_filtered[["id", "date", "details", "amount", "direction", "modified"]].copy()
    
    # Behandle die date-Spalte richtig
    editable_df["date"] = editable_df["date"].dt.date  # Konvertiere datetime in date 
    editable_df["modified"] = editable_df["modified"].fillna(False)
    
    # Spalten für die Anzeige benennen
    editable_display = editable_df.drop(columns=["id", "modified"]).rename(columns={
        "date": "Datum",
        "details": "Buchungsdetails",
        "amount": "Betrag",
        "direction": "Art"
    })
    
    # Anzeige der editierbaren Tabelle mit mehr Platz
    st.subheader("Buchungen bearbeiten")
    
    # Hilfetexte einklappen (default geschlossen)
    with st.expander("ℹ️ Hilfe zur Bearbeitung", expanded=False):
        st.markdown("""
        ### Tipps zur Bearbeitung:
        1. **Datum**: Klicke auf das Datum, um einen Datepicker zu öffnen
        2. **Betrag**: Gib den Betrag als Zahl ein (wird automatisch im CHF-Format angezeigt)
        3. **Art**: Wähle zwischen 'Incoming' (Einnahme) und 'Outgoing' (Ausgabe)
        4. **Hinzufügen**: Neue Zeilen werden automatisch hinzugefügt, wenn du in der letzten Zeile schreibst
        5. **Speichern**: Änderungen werden automatisch gespeichert, wenn du eine andere Zelle auswählst
        """)
    
    # Tabelle mit maximaler Höhe anzeigen
    edited_df = st.data_editor(
        editable_display,
        num_rows="dynamic",
        use_container_width=True,
        height=700,  # Großzügige Höhe für viele Einträge
        hide_index=True,
        column_config={
            "Art": st.column_config.SelectboxColumn(
                "Art",
                options=["Incoming", "Outgoing"],
                help="Typ der Buchung"
            ),
            "Betrag": st.column_config.NumberColumn(
                "Betrag",
                format="%.2f CHF", 
                help="Betrag in CHF"
            ),
            # Verwende DateColumn mit korrekten dtype
            "Datum": st.column_config.DateColumn(
                "Datum",
                help="Datum der Buchung",
                format="DD.MM.YYYY",
                min_value=date(2020, 1, 1),
                max_value=date(2030, 12, 31),
                step=1
            )
        }
    )

    # Verarbeitung der Änderungen
    if edited_df is not None:
        try:
            # Spalten zurückwandeln
            edited_df.columns = ["date", "details", "amount", "direction"]
            
            # Daten konvertieren
            # Datum ist bereits ein date-Objekt, muss nicht geparst werden
            edited_df["amount"] = pd.to_numeric(edited_df["amount"], errors="coerce")
            edited_df = edited_df.dropna(subset=["date", "amount"]).reset_index(drop=True)

            modified_ids = []
            modified_rows = []
            
            # Wenn Anzahl der Zeilen nicht übereinstimmt, gibt es neue Einträge
            has_new_rows = len(edited_df) > len(editable_df)
            
            # Bestehende Zeilen durchgehen und auf Änderungen prüfen
            for idx in range(min(len(edited_df), len(editable_df))):
                if idx >= len(df_filtered):
                    continue
                    
                original = df_filtered.iloc[idx]
                edited = edited_df.iloc[idx]

                # Prüfe ob sich etwas geändert hat
                # Konvertiere date zu date für Vergleich
                original_date = original["date"].date() if hasattr(original["date"], "date") else original["date"]
                
                is_modified = (
                    original_date != edited["date"]
                    or original["details"] != edited["details"]
                    or original["direction"] != edited["direction"]
                    or abs(original["amount"] - edited["amount"]) > 0.01
                )

                if is_modified:
                    try:
                        # Konvertiere date zu string im Format YYYY-MM-DD
                        date_str = edited["date"].strftime("%Y-%m-%d")
                        
                        update_buchung_by_id(
                            id=original["id"],
                            date=date_str,
                            details=edited["details"],
                            amount=round(edited["amount"], 2),
                            direction=edited["direction"]
                        )
                        modified_ids.append(original["id"])
                        modified_rows.append(idx)
                    except Exception as update_error:
                        st.error(f"Fehler beim Aktualisieren von Eintrag {idx+1}: {update_error}")
            
            # Neue Zeilen hinzufügen
            if has_new_rows:
                for idx in range(len(editable_df), len(edited_df)):
                    edited = edited_df.iloc[idx]
                    # Neue Buchung zur Datenbank hinzufügen
                    # Hier muss noch die Implementierung für das Hinzufügen erfolgen
                    # Da dies in den aktuellen Dateien nicht vorhanden ist
                    st.info(f"Neue Zeile erkannt in Zeile {idx+1}. Hinzufügen von neuen Einträgen wird in einer zukünftigen Version implementiert.")

            if modified_ids:
                st.success(f"✔️ {len(modified_ids)} Änderung(en) gespeichert.")
                
                # Zeige geänderte Zeilen an
                with st.expander("Geänderte Zeilen anzeigen", expanded=False):
                    for idx in modified_rows:
                        st.write(f"Zeile {idx+1}: {edited_df.iloc[idx]['details']}")
            else:
                if not has_new_rows:
                    st.info("Keine Änderungen erkannt.")

            # Session aktualisieren
            updated_df = load_buchungen()
            st.session_state.edited_df = updated_df.copy()

        except Exception as e:
            st.error(f"❌ Fehler beim Verarbeiten: {e}")
            st.exception(e)  # Zeige vollständigen Fehler für Debugging