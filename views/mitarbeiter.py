import streamlit as st
import pandas as pd
from datetime import datetime, date
from logic.storage_mitarbeiter import (
    load_mitarbeiter, 
    save_mitarbeiter, 
    add_mitarbeiter,
    update_mitarbeiter,
    delete_mitarbeiter,
    add_lohn_to_mitarbeiter,
    update_lohn,
    delete_lohn,
    get_aktuelle_loehne
)
from core.parsing import parse_date_swiss_fallback
from core.utils import chf_format
from core.auth import prüfe_session_gültigkeit, log_user_activity

def show():
    # Authentifizierungsprüfung
    if not prüfe_session_gültigkeit():
        st.warning("Bitte melden Sie sich an, um auf diesen Bereich zuzugreifen")
        st.stop()
    
    # Benutzer-ID für Audit-Protokollierung
    user_id = st.session_state.user.id
    
    st.header("👥 Mitarbeiter & Lohnverwaltung")
    
    # Session-State für Aktualisierungen
    if "mitarbeiter_aktualisiert" not in st.session_state:
        st.session_state.mitarbeiter_aktualisiert = False
        
    if st.session_state.mitarbeiter_aktualisiert:
        st.session_state.mitarbeiter_aktualisiert = False
        st.rerun()
    
    # Alle Mitarbeiter laden (ohne Benutzerfilterung)
    mitarbeiter_list = load_mitarbeiter()
    
    # Aktivität protokollieren
    log_user_activity("Mitarbeiterverwaltung aufgerufen", {
        "anzahl_mitarbeiter": len(mitarbeiter_list) if mitarbeiter_list else 0
    })

    # Einführung
    with st.expander("ℹ️ Über die Mitarbeiterverwaltung", expanded=False):
        st.markdown("""
        ### Mitarbeiter & Lohnverwaltung
        
        In diesem Bereich kannst du:
        
        - Mitarbeiter hinzufügen und verwalten
        - Lohndaten mit Start- und Enddatum erfassen
        - Lohnverläufe dokumentieren
        - Bestehende Einträge bearbeiten oder löschen
        
        Die erfassten Lohndaten werden automatisch in der Liquiditätsplanung berücksichtigt.
        **Hinweis:** Die Löhne werden jeweils am 25. des Monats ausgezahlt.
        """)
    
    # ===== NEUEN MITARBEITER HINZUFÜGEN =====
    st.subheader("➕ Neuen Mitarbeiter hinzufügen")
    
    with st.form("mitarbeiter_form"):
        # Zeile 1: Name und Lohn
        col1, col2 = st.columns([2, 2])
        with col1:
            name = st.text_input("Name des Mitarbeiters", placeholder="z.B. Max Muster")
        with col2:
            lohn_betrag = st.text_input("Lohn (CHF)", placeholder="z.B. 5'500.00")
        
        # Zeile 2: Start- und Enddatum
        col3, col4 = st.columns(2)
        with col3:
            lohn_start = st.date_input("Lohn gültig ab", value=date.today())
        
        # Options für Enddatum
        with col4:
            ende_leer = st.checkbox("Unbefristet (kein Enddatum)", value=True, key="new_mitarbeiter_unbefristet")
            if ende_leer:
                lohn_ende = None
                st.text("Enddatum: Unbefristet")
            else:
                lohn_ende = st.date_input("Lohn gültig bis", value=date.today())
        
        # Hinzufügen-Button
        submitted = st.form_submit_button("✅ Mitarbeiter hinzufügen")
        
        if submitted:
            if not name.strip():
                st.error("❌ Bitte gib einen Namen ein.")
            elif not lohn_betrag.strip():
                st.error("❌ Bitte gib einen Lohnbetrag ein.")
            else:
                try:
                    # Lohnbetrag konvertieren
                    lohn_num = float(lohn_betrag.replace("'", "").replace(",", "."))
                    
                    # Lohndaten erstellen
                    lohn_daten = [{
                        "Start": lohn_start.strftime("%Y-%m-%d"),
                        "Ende": lohn_ende.strftime("%Y-%m-%d") if lohn_ende else None,
                        "Betrag": lohn_num
                    }]
                    
                    # Aktuelle Zeit für Timestamps
                    now = datetime.now().isoformat()
                    
                    # Mitarbeiter hinzufügen mit Benutzer-ID
                    if add_mitarbeiter(name.strip(), lohn_daten, user_id=user_id, created_at=now, updated_at=now):
                        # Aktivität protokollieren
                        log_user_activity("Mitarbeiter hinzugefügt", {
                            "name": name.strip(),
                            "lohn": lohn_num,
                            "start": lohn_start.isoformat()
                        })
                        
                        st.success(f"✅ Mitarbeiter '{name}' erfolgreich hinzugefügt")
                        st.session_state.mitarbeiter_aktualisiert = True
                        st.rerun()
                    else:
                        st.error("❌ Fehler beim Hinzufügen des Mitarbeiters")
                        
                        # Fehler protokollieren
                        log_user_activity("Fehler beim Hinzufügen von Mitarbeiter", {
                            "name": name.strip(),
                            "fehler": "Hinzufügen fehlgeschlagen"
                        })
                        
                except ValueError:
                    st.error("❌ Bitte gib einen gültigen Lohnbetrag ein.")
    
    # Trennlinie
    st.markdown("---")
    
    # ===== BESTEHENDE MITARBEITER ANZEIGEN =====
    st.subheader("💼 Mitarbeiter verwalten")
    
    # Protokollierung der Ansicht
    log_user_activity("Mitarbeiterverwaltung angesehen", {
        "anzahl_mitarbeiter": len(mitarbeiter_list) if mitarbeiter_list else 0
    })
    
    if not mitarbeiter_list:
        st.info("Noch keine Mitarbeiter erfasst. Füge oben einen neuen Mitarbeiter hinzu.")
    else:
        # Liste aller aktuellen Mitarbeiter
        for m_index, mitarbeiter in enumerate(mitarbeiter_list):
            m_id = mitarbeiter.get("id", f"m{m_index}")
            m_name = mitarbeiter.get("Name", "Unbekannter Mitarbeiter")
            
            # Lohndaten extrahieren und sortieren
            lohn_daten = mitarbeiter.get("Lohn", [])
            
            # Aktuellen Lohn bestimmen (nach Startdatum sortiert, neuestes zuerst)
            sorted_lohn = sorted(
                lohn_daten, 
                key=lambda x: datetime.strptime(x["Start"], "%Y-%m-%d") if isinstance(x["Start"], str) else x["Start"],
                reverse=True
            )
            
            aktueller_lohn = None
            if sorted_lohn:
                heute = date.today()
                for lohn in sorted_lohn:
                    start_date = datetime.strptime(lohn["Start"], "%Y-%m-%d").date() if isinstance(lohn["Start"], str) else lohn["Start"]
                    
                    # Ende-Datum prüfen
                    ende_date = None
                    if lohn.get("Ende") and lohn.get("Ende") != "None":
                        ende_date = datetime.strptime(lohn["Ende"], "%Y-%m-%d").date() if isinstance(lohn["Ende"], str) else lohn["Ende"]
                    
                    # Prüfen, ob der Lohn aktuell gültig ist
                    if start_date <= heute and (ende_date is None or ende_date >= heute):
                        aktueller_lohn = lohn
                        break
                
                # Falls kein aktuell gültiger Lohn gefunden wurde, nehmen wir den neuesten
                if not aktueller_lohn and sorted_lohn:
                    aktueller_lohn = sorted_lohn[0]
            
            # Titel für den Expander
            if aktueller_lohn:
                lohn_betrag = chf_format(aktueller_lohn["Betrag"])
                expander_title = f"{m_name} – {lohn_betrag}"
            else:
                expander_title = f"{m_name} – Kein Lohn hinterlegt"
            
            # Mitarbeiter im Expander anzeigen
            with st.expander(expander_title, expanded=False):
                # Mitarbeiter-Details bearbeiten
                with st.form(key=f"form_mitarbeiter_{m_id}"):
                    st.markdown(f"#### 👤 {m_name}")
                    
                    # Name bearbeiten
                    edit_name = st.text_input("Name", value=m_name, key=f"name_{m_id}")
                    
                    # Speichern-Button
                    if st.form_submit_button("💾 Mitarbeiter-Daten speichern"):
                        if not edit_name.strip():
                            st.error("❌ Der Name darf nicht leer sein.")
                        else:
                            # Originale Daten für Audit-Logs
                            original_name = m_name
                            
                            # Aktualisierte Mitarbeiterdaten
                            updated_data = {
                                "Name": edit_name.strip(),
                                "Lohn": mitarbeiter.get("Lohn", []),
                                "user_id": user_id,  # Benutzer-ID beibehalten
                                "updated_at": datetime.now().isoformat()  # Aktualisierungszeitstempel
                            }
                            
                            if update_mitarbeiter(m_id, updated_data):
                                # Aktivität protokollieren
                                log_user_activity("Mitarbeiter bearbeitet", {
                                    "id": m_id,
                                    "original": {"name": original_name},
                                    "neu": {"name": edit_name.strip()}
                                })
                                
                                st.success("✅ Mitarbeiter-Daten gespeichert")
                                st.session_state.mitarbeiter_aktualisiert = True
                                st.rerun()
                            else:
                                st.error("❌ Fehler beim Speichern der Mitarbeiter-Daten")
                                
                                # Fehler protokollieren
                                log_user_activity("Fehler beim Bearbeiten von Mitarbeiter", {
                                    "id": m_id,
                                    "fehler": "Bearbeiten fehlgeschlagen"
                                })
                
                # Lohndaten anzeigen
                st.markdown("#### 💰 Lohnverlauf")
                
                if not lohn_daten:
                    st.info("Noch keine Lohndaten für diesen Mitarbeiter erfasst.")
                else:
                    # Tabelle mit allen Lohndaten
                    lohn_df = []
                    for lohn_index, lohn in enumerate(sorted_lohn):
                        lohn_start = datetime.strptime(lohn["Start"], "%Y-%m-%d").date() if isinstance(lohn["Start"], str) else lohn["Start"]
                        
                        # Ende-Datum verarbeiten
                        if lohn.get("Ende") and lohn.get("Ende") != "None":
                            lohn_ende = datetime.strptime(lohn["Ende"], "%Y-%m-%d").date() if isinstance(lohn["Ende"], str) else lohn["Ende"]
                            ende_text = lohn_ende.strftime("%d.%m.%Y")
                        else:
                            lohn_ende = None
                            ende_text = "unbefristet"
                            
                        lohn_df.append({
                            "Index": lohn_index,
                            "Betrag": chf_format(lohn["Betrag"]),
                            "Gültig ab": lohn_start.strftime("%d.%m.%Y"),
                            "Gültig bis": ende_text
                        })
                    
                    lohn_dataframe = pd.DataFrame(lohn_df)
                    st.dataframe(lohn_dataframe, use_container_width=True)
                    
                    # Lohndaten bearbeiten (einzeln) - HIER IST DER EINDEUTIGE KEY WICHTIG!
                    selected_lohn_index = st.selectbox(
                        "Lohneintrag zum Bearbeiten auswählen:", 
                        options=range(len(sorted_lohn)),
                        format_func=lambda x: f"Lohn {x+1}: {lohn_df[x]['Betrag']} (ab {lohn_df[x]['Gültig ab']})",
                        key=f"select_lohn_{m_id}"  # Eindeutiger Key für jede Selectbox
                    )
                    
                    lohn = sorted_lohn[selected_lohn_index]
                    lohn_id = f"{m_id}_lohn_{selected_lohn_index}"
                    
                    # Datum für die Formular-Anzeige konvertieren
                    lohn_start = datetime.strptime(lohn["Start"], "%Y-%m-%d").date() if isinstance(lohn["Start"], str) else lohn["Start"]
                    
                    # Ende-Datum verarbeiten
                    if lohn.get("Ende") and lohn.get("Ende") != "None":
                        lohn_ende = datetime.strptime(lohn["Ende"], "%Y-%m-%d").date() if isinstance(lohn["Ende"], str) else lohn["Ende"]
                        hat_ende = False
                    else:
                        lohn_ende = None
                        hat_ende = True
                    
                    # Lohndaten bearbeiten
                    with st.form(key=f"form_lohn_{lohn_id}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            edit_betrag = st.text_input(
                                "Lohn (CHF)", 
                                value=str(lohn["Betrag"]).replace(".", ","), 
                                key=f"betrag_{lohn_id}"
                            )
                        with col2:
                            edit_start = st.date_input(
                                "Gültig ab", 
                                value=lohn_start, 
                                key=f"start_{lohn_id}"
                            )
                        
                        # Optionales Enddatum mit Checkbox
                        unbefristet = st.checkbox(
                            "Unbefristet (kein Enddatum)", 
                            value=hat_ende, 
                            key=f"unbefristet_{lohn_id}"
                        )
                        
                        if not unbefristet:
                            edit_ende = st.date_input(
                                "Gültig bis", 
                                value=lohn_ende if lohn_ende else date.today(), 
                                key=f"ende_{lohn_id}"
                            )
                        else:
                            edit_ende = None
                            st.text("Gültig bis: Unbefristet")
                        
                        # Speichern-Button für Lohndaten
                        col_save, col_delete = st.columns(2)
                        with col_save:
                            save_lohn = st.form_submit_button("💾 Lohndaten speichern")
                        with col_delete:
                            delete_lohn_button = st.form_submit_button("🗑️ Lohneintrag löschen")
                        
                        if save_lohn:
                            try:
                                # Lohnbetrag konvertieren
                                lohn_num = float(edit_betrag.replace("'", "").replace(",", "."))
                                
                                # Originale Daten für Audit-Logs
                                original_lohn = {
                                    "betrag": float(lohn["Betrag"]),
                                    "start": lohn_start.isoformat() if hasattr(lohn_start, "isoformat") else str(lohn_start),
                                    "ende": lohn_ende.isoformat() if lohn_ende and hasattr(lohn_ende, "isoformat") else None
                                }
                                
                                # Aktualisierte Lohndaten
                                updated_lohn = {
                                    "Start": edit_start.strftime("%Y-%m-%d"),
                                    "Ende": edit_ende.strftime("%Y-%m-%d") if edit_ende else None,
                                    "Betrag": lohn_num
                                }
                                
                                if update_lohn(m_id, selected_lohn_index, updated_lohn, user_id=user_id):
                                    # Aktivität protokollieren
                                    log_user_activity("Lohndaten bearbeitet", {
                                        "mitarbeiter_id": m_id,
                                        "mitarbeiter_name": m_name,
                                        "original": original_lohn,
                                        "neu": {
                                            "betrag": lohn_num,
                                            "start": edit_start.isoformat(),
                                            "ende": edit_ende.isoformat() if edit_ende else None
                                        }
                                    })
                                    
                                    st.success("✅ Lohndaten gespeichert")
                                    st.session_state.mitarbeiter_aktualisiert = True
                                    st.rerun()
                                else:
                                    st.error("❌ Fehler beim Speichern der Lohndaten")
                                    
                                    # Fehler protokollieren
                                    log_user_activity("Fehler beim Bearbeiten von Lohndaten", {
                                        "mitarbeiter_id": m_id,
                                        "mitarbeiter_name": m_name,
                                        "fehler": "Bearbeiten fehlgeschlagen"
                                    })
                            except ValueError:
                                st.error("❌ Bitte gib einen gültigen Lohnbetrag ein.")
                        
                        if delete_lohn_button:
                            if delete_lohn(m_id, selected_lohn_index, user_id=user_id):
                                # Aktivität protokollieren
                                log_user_activity("Lohneintrag gelöscht", {
                                    "mitarbeiter_id": m_id,
                                    "mitarbeiter_name": m_name,
                                    "betrag": float(lohn["Betrag"]),
                                    "start": lohn_start.isoformat() if hasattr(lohn_start, "isoformat") else str(lohn_start)
                                })
                                
                                st.success("✅ Lohneintrag gelöscht")
                                st.session_state.mitarbeiter_aktualisiert = True
                                st.rerun()
                            else:
                                st.error("❌ Fehler beim Löschen des Lohneintrags")
                                
                                # Fehler protokollieren
                                log_user_activity("Fehler beim Löschen von Lohneintrag", {
                                    "mitarbeiter_id": m_id,
                                    "mitarbeiter_name": m_name,
                                    "fehler": "Löschen fehlgeschlagen"
                                })
                
                # Neuen Lohneintrag hinzufügen
                st.markdown("#### Neuen Lohneintrag hinzufügen")
                with st.form(key=f"form_new_lohn_{m_id}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        new_lohn = st.text_input(
                            "Neuer Lohn (CHF)", 
                            placeholder="z.B. 5'800.00", 
                            key=f"new_lohn_{m_id}"
                        )
                    with col2:
                        new_start = st.date_input(
                            "Gültig ab", 
                            value=date.today(), 
                            key=f"new_start_{m_id}"
                        )
                    
                    # Checkbox für unbefristeten Lohn
                    unbefristet_neu = st.checkbox(
                        "Unbefristet (kein Enddatum)", 
                        value=True, 
                        key=f"new_unbefristet_{m_id}"
                    )
                    
                    if not unbefristet_neu:
                        new_ende = st.date_input(
                            "Gültig bis", 
                            value=date.today(), 
                            key=f"new_ende_{m_id}"
                        )
                    else:
                        new_ende = None
                        st.text("Gültig bis: Unbefristet")
                    
                    if st.form_submit_button("➕ Lohn hinzufügen"):
                        if not new_lohn.strip():
                            st.error("❌ Bitte gib einen Lohnbetrag ein.")
                        else:
                            try:
                                # Lohnbetrag konvertieren
                                lohn_num = float(new_lohn.replace("'", "").replace(",", "."))
                                
                                # Lohndaten erstellen
                                lohn_daten = {
                                    "Start": new_start.strftime("%Y-%m-%d"),
                                    "Ende": new_ende.strftime("%Y-%m-%d") if new_ende else None,
                                    "Betrag": lohn_num
                                }
                                
                                if add_lohn_to_mitarbeiter(m_id, lohn_daten, user_id=user_id):
                                    # Aktivität protokollieren
                                    log_user_activity("Lohneintrag hinzugefügt", {
                                        "mitarbeiter_id": m_id,
                                        "mitarbeiter_name": m_name,
                                        "betrag": lohn_num,
                                        "start": new_start.isoformat(),
                                        "ende": new_ende.isoformat() if new_ende else None
                                    })
                                    
                                    st.success("✅ Lohn erfolgreich hinzugefügt")
                                    st.session_state.mitarbeiter_aktualisiert = True
                                    st.rerun()
                                else:
                                    st.error("❌ Fehler beim Hinzufügen des Lohns")
                                    
                                    # Fehler protokollieren
                                    log_user_activity("Fehler beim Hinzufügen von Lohneintrag", {
                                        "mitarbeiter_id": m_id,
                                        "mitarbeiter_name": m_name,
                                        "fehler": "Hinzufügen fehlgeschlagen"
                                    })
                            except ValueError:
                                st.error("❌ Bitte gib einen gültigen Lohnbetrag ein.")
                
                # Mitarbeiter löschen
                st.markdown("---")
                if st.button("🗑️ Mitarbeiter löschen", key=f"delete_{m_id}"):
                    st.session_state[f"confirm_delete_{m_id}"] = True
                    st.rerun()
                
                # Löschen bestätigen, wenn der Button geklickt wurde
                if st.session_state.get(f"confirm_delete_{m_id}", False):
                    st.warning(f"⚠️ Willst du den Mitarbeiter '{m_name}' wirklich löschen? Alle zugehörigen Lohndaten werden ebenfalls gelöscht.")
                    confirm_col1, confirm_col2 = st.columns(2)
                    with confirm_col1:
                        if st.button("❌ Ja, löschen", key=f"confirm_yes_{m_id}"):
                            if delete_mitarbeiter(m_id, user_id=user_id):
                                # Aktivität protokollieren
                                log_user_activity("Mitarbeiter gelöscht", {
                                    "id": m_id,
                                    "name": m_name
                                })
                                
                                st.success("✅ Mitarbeiter erfolgreich gelöscht")
                                if f"confirm_delete_{m_id}" in st.session_state:
                                    del st.session_state[f"confirm_delete_{m_id}"]
                                st.session_state.mitarbeiter_aktualisiert = True
                                st.rerun()
                            else:
                                st.error("❌ Löschen fehlgeschlagen")
                                
                                # Fehler protokollieren
                                log_user_activity("Fehler beim Löschen von Mitarbeiter", {
                                    "id": m_id,
                                    "name": m_name,
                                    "fehler": "Löschen fehlgeschlagen"
                                })
                    with confirm_col2:
                        if st.button("Abbrechen", key=f"confirm_no_{m_id}"):
                            if f"confirm_delete_{m_id}" in st.session_state:
                                del st.session_state[f"confirm_delete_{m_id}"]
                            st.rerun()
        
        # ===== ÜBERSICHT AKTUELLE LÖHNE =====
        st.markdown("---")
        st.subheader("📊 Übersicht aktuelle Löhne")
        
        # Löhne ohne Benutzerfilterung laden
        aktuelle_loehne = get_aktuelle_loehne()
        
        if not aktuelle_loehne:
            st.info("Keine aktuell gültigen Löhne gefunden.")
        else:
            # DataFrame erstellen
            df_loehne = pd.DataFrame(aktuelle_loehne)
            
            # Betrag formatieren - sicherstellen, dass es vorher kein String ist
            df_loehne["Betrag_Anzeige"] = df_loehne["Betrag"].apply(lambda x: chf_format(x))
            
            # Datumsfelder formatieren, falls vorhanden
            if "Start" in df_loehne.columns:
                df_loehne["Start"] = df_loehne["Start"].apply(lambda x: x.strftime("%d.%m.%Y") if x else "")
            
            if "Ende" in df_loehne.columns:
                df_loehne["Ende"] = df_loehne["Ende"].apply(lambda x: x.strftime("%d.%m.%Y") if x else "unbefristet")
            
            # Spalten für die Anzeige auswählen und umbenennen
            df_view = df_loehne[["Mitarbeiter", "Betrag_Anzeige", "Start", "Ende"]]
            df_view = df_view.rename(columns={
                "Betrag_Anzeige": "Betrag",
                "Start": "Gültig ab",
                "Ende": "Gültig bis"
            })
            
            # Tabelle anzeigen
            st.dataframe(df_view, use_container_width=True)
            
            # Gesamtsumme berechnen und anzeigen - direkt aus numerischen Werten
            summe = sum(float(row["Betrag"]) for row in aktuelle_loehne)
            st.markdown(f"**Monatliche Lohnsumme: {chf_format(summe)}**")
            st.markdown(f"**Auszahlung erfolgt am 25. des Monats**")
            
            # Übersicht protokollieren
            log_user_activity("Lohnübersicht angesehen", {
                "anzahl_loehne": len(aktuelle_loehne),
                "monatliche_summe": summe
            })