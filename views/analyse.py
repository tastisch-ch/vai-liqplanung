import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from core.parsing import parse_date_swiss_fallback
from core.utils import chf_format
from streamlit_echarts import st_echarts
from logic.storage_fixkosten import convert_fixkosten_to_buchungen, load_fixkosten
from logic.storage_simulation import convert_simulationen_to_buchungen
from logic.storage_mitarbeiter import convert_loehne_to_buchungen, get_aktuelle_loehne
from logic.storage_buchungen import load_buchungen

def show():
    st.header("📈 Analyse")

    # Planungszeitraum festlegen
    default_start = date.today()
    default_end = default_start + timedelta(days=270)  # Standard: 9 Monate
    
    # Session-State für Datumswerte verwenden
    if "analyse_start_date" not in st.session_state:
        st.session_state.analyse_start_date = default_start
    if "analyse_end_date" not in st.session_state:
        st.session_state.analyse_end_date = default_end
    
    # Funktion für den Button
    def set_three_months():
        st.session_state.analyse_start_date = date.today()
        st.session_state.analyse_end_date = date.today() + timedelta(days=90)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        start_date = st.date_input("Startdatum für Analyse", 
                                   value=st.session_state.analyse_start_date,
                                   key="start_date_input")
        st.session_state.analyse_start_date = start_date
    with col2:
        end_date = st.date_input("Enddatum für Analyse", 
                                 value=st.session_state.analyse_end_date,
                                 key="end_date_input")
        st.session_state.analyse_end_date = end_date
    with col3:
        st.button("Aktuelle 3 Monate anzeigen", on_click=set_three_months)
    
    # Optionen für die Anzeige
    col_options = st.columns(4)
    with col_options[0]:
        show_fixkosten = st.checkbox("Fixkosten einbeziehen", value=True)
    with col_options[1]:
        show_simulationen = st.checkbox("Simulationen einbeziehen", value=True)
    with col_options[2]:
        show_loehne = st.checkbox("Lohnauszahlungen einbeziehen", value=True)
    with col_options[3]:
        show_daily_points = st.checkbox("Alle Tage anzeigen", value=True)

    # Daten laden - auch wenn keine Daten im Editor bearbeitet wurden
    if "edited_df" in st.session_state:
        df = st.session_state.edited_df.copy()
    else:
        df = load_buchungen()
        if df is None or df.empty:
            # Leeren DataFrame erstellen für die weitere Verarbeitung
            df = pd.DataFrame(columns=["date", "details", "amount", "direction"])
    
    # Spaltennamen normalisieren - hier verwenden wir Großbuchstaben, da das die Konvention in diesem Modul ist
    df = df.copy()
    df.columns = df.columns.str.capitalize()
    
    if not df.empty:
        df["Date"] = pd.to_datetime(df["Date"])
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
        # Nach Datum filtern
        df = df[(df["Date"].dt.date >= start_date) & (df["Date"].dt.date <= end_date)]
    
    df = df.sort_values("Date").reset_index(drop=True)

    # Fixkosten laden, wenn aktiviert
    if show_fixkosten:
        try:
            fixkosten_df = convert_fixkosten_to_buchungen(start_date, end_date)
            
            if not fixkosten_df.empty:
                # Sicherstellen, dass die Spalten kompatibel sind
                fixkosten_df.columns = fixkosten_df.columns.str.capitalize()
                
                # Füge eine Kategorie-Spalte hinzu
                if "Kategorie" not in df.columns:
                    df["Kategorie"] = "Standard"
                
                if "Kategorie" not in fixkosten_df.columns:
                    fixkosten_df["Kategorie"] = "Fixkosten"
                
                # Sicherstellen, dass Direction immer outgoing ist für Fixkosten
                fixkosten_df["Direction"] = "Outgoing"
                
                # Kombiniere die Dataframes
                combined_df = pd.concat([df, fixkosten_df], ignore_index=True)
                combined_df = combined_df.sort_values("Date").reset_index(drop=True)
                
                df = combined_df
                st.success(f"✅ {len(fixkosten_df)} Fixkosten in die Analyse integriert")
        except Exception as e:
            st.error(f"❌ Fehler beim Laden der Fixkosten: {e}")

    # Simulationen laden, wenn aktiviert
    if show_simulationen:
        try:
            simulation_df = convert_simulationen_to_buchungen()
            
            if not simulation_df.empty:
                # Spaltennamen normalisieren
                simulation_df.columns = simulation_df.columns.str.capitalize()
                
                # Nach Datum filtern
                simulation_df["Date"] = pd.to_datetime(simulation_df["Date"])
                simulation_df = simulation_df[(simulation_df["Date"].dt.date >= start_date) & 
                                             (simulation_df["Date"].dt.date <= end_date)]
                
                if "Kategorie" not in df.columns:
                    df["Kategorie"] = "Standard"
                
                if "Kategorie" not in simulation_df.columns:
                    simulation_df["Kategorie"] = "Simulation"
                
                # Kombiniere die Dataframes
                combined_df = pd.concat([df, simulation_df], ignore_index=True)
                combined_df = combined_df.sort_values("Date").reset_index(drop=True)
                
                df = combined_df
                st.success(f"✅ {len(simulation_df)} Simulationen in die Analyse integriert")
        except Exception as e:
            st.error(f"❌ Fehler beim Laden der Simulationen: {e}")

    # Lohndaten laden, wenn aktiviert
    if show_loehne:
        try:
            lohn_df = convert_loehne_to_buchungen(start_date, end_date)
            
            if not lohn_df.empty:
                # Spaltennamen normalisieren
                lohn_df.columns = lohn_df.columns.str.capitalize()
                
                if "Kategorie" not in df.columns:
                    df["Kategorie"] = "Standard"
                
                if "Kategorie" not in lohn_df.columns:
                    lohn_df["Kategorie"] = "Lohn"
                
                # Sicherstellen, dass Direction immer outgoing ist für Löhne
                lohn_df["Direction"] = "Outgoing"
                
                # Kombiniere die Dataframes
                combined_df = pd.concat([df, lohn_df], ignore_index=True)
                combined_df = combined_df.sort_values("Date").reset_index(drop=True)
                
                df = combined_df
                st.success(f"✅ {len(lohn_df)} Lohnbuchungen in die Analyse integriert")
        except Exception as e:
            st.error(f"❌ Fehler beim Laden der Lohndaten: {e}")

    # Wenn nach dem Laden immer noch keine Daten vorhanden sind
    if df.empty:
        st.warning("Keine Daten für die Analyse verfügbar.")
        return

    # Beträge entsprechend der Richtung anpassen
    df["Amount"] = df.apply(
        lambda row: -abs(float(row["Amount"])) if row["Direction"].lower() == "outgoing" else abs(float(row["Amount"])),
        axis=1
    )
    
    start_balance = st.session_state.get("start_balance", 0)
    
    # Kontostand berechnen (nach Datum sortiert)
    df_sorted = df.sort_values("Date").reset_index(drop=True)
    df_sorted["Kontostand"] = df_sorted["Amount"].cumsum() + start_balance
    
    # Sortierte Indizes auf ursprüngliche Sortierung anwenden
    kontostand_mapping = dict(zip(df_sorted.index, df_sorted["Kontostand"]))
    df["Kontostand"] = df.index.map(kontostand_mapping)

    # NEUE FEATURE: Monatliche Übersicht (aus planung.py übernommen und angepasst)
    st.subheader("💰 Monatliche Übersicht")
    
    if not df.empty:
        # Monatlich gruppieren
        df["Month"] = df["Date"].dt.strftime("%Y-%m")
        monthly_summary = df.groupby(["Month", "Direction"])["Amount"].sum().unstack().fillna(0)
        
        if "Incoming" in monthly_summary.columns and "Outgoing" in monthly_summary.columns:
            # Saldo berechnen (outgoing ist bereits negativ)
            monthly_summary["Saldo"] = monthly_summary["Incoming"] + monthly_summary["Outgoing"]
            
            # Formatierung
            formatted_summary = monthly_summary.copy()
            for col in formatted_summary.columns:
                formatted_summary[col] = formatted_summary[col].apply(chf_format)
            
            # Anzeige der monatlichen Übersicht
            st.dataframe(
                formatted_summary.rename(columns={
                    "Incoming": "Einnahmen",
                    "Outgoing": "Ausgaben"
                }), 
                use_container_width=True
            )
    
    # Monatsübersicht
    st.subheader("💡 Monatsübersicht (Diagramm)")
    df["Monat"] = df["Date"].dt.to_period("M").astype(str)
    
    try:
        # Unterscheidung zwischen Fixkosten, Simulationen, Löhnen und anderen Buchungen
        if "Kategorie" in df.columns:
            monthly = df.groupby(["Monat", "Direction", "Kategorie"])["Amount"].sum().unstack().fillna(0)
            
            months = sorted(df["Monat"].unique().tolist())
            
            # Separate Darstellung für verschiedene Kategorien
            incoming = []
            outgoing_standard = []
            outgoing_fixkosten = []
            outgoing_simulation = []
            outgoing_lohn = []
            kontostand = []
            
            # Temporärer DataFrame für Kontostand-Berechnung
            temp_df = df.sort_values("Date").copy()
            temp_df["running_total"] = temp_df["Amount"].cumsum() + start_balance
            
            for month in months:
                # Einnahmen (alle Kategorien zusammen)
                month_incoming = df[(df["Monat"] == month) & (df["Direction"].str.lower() == "incoming")]["Amount"].sum()
                incoming.append(month_incoming)
                
                # Ausgaben nach Kategorien
                month_outgoing_standard = abs(df[(df["Monat"] == month) & 
                                           (df["Direction"].str.lower() == "outgoing") & 
                                           (df["Kategorie"] == "Standard")]["Amount"].sum())
                outgoing_standard.append(month_outgoing_standard)
                
                month_outgoing_fixkosten = abs(df[(df["Monat"] == month) & 
                                            (df["Direction"].str.lower() == "outgoing") & 
                                            (df["Kategorie"] == "Fixkosten")]["Amount"].sum())
                outgoing_fixkosten.append(month_outgoing_fixkosten)
                
                month_outgoing_simulation = abs(df[(df["Monat"] == month) & 
                                             (df["Direction"].str.lower() == "outgoing") & 
                                             (df["Kategorie"] == "Simulation")]["Amount"].sum())
                outgoing_simulation.append(month_outgoing_simulation)
                
                month_outgoing_lohn = abs(df[(df["Monat"] == month) & 
                                        (df["Direction"].str.lower() == "outgoing") & 
                                        (df["Kategorie"] == "Lohn")]["Amount"].sum())
                outgoing_lohn.append(month_outgoing_lohn)
                
                # Letzter Kontostand des Monats
                month_end = temp_df[temp_df["Monat"] == month]["running_total"].iloc[-1] if len(temp_df[temp_df["Monat"] == month]) > 0 else (kontostand[-1] if kontostand else start_balance)
                kontostand.append(month_end)
            
            # Erweitertes Chart mit allen Kategorien
            chart = {
                "tooltip": {"trigger": "axis"},
                "legend": {
                    "data": ["Einnahmen", "Ausgaben (Standard)", "Ausgaben (Fixkosten)", 
                             "Ausgaben (Simulation)", "Ausgaben (Lohn)", "Kontostand"]
                },
                "xAxis": {"type": "category", "data": months},
                "yAxis": {"type": "value"},
                "toolbox": {
                    "feature": {
                        "dataZoom": {
                            "yAxisIndex": "none"
                        },
                        "restore": {},
                        "saveAsImage": {}
                    }
                },
                "dataZoom": [
                    {
                        "type": "inside",
                        "start": 0,
                        "end": 100
                    },
                    {
                        "start": 0,
                        "end": 100
                    }
                ],
                "series": [
                    {
                        "name": "Einnahmen", 
                        "type": "bar", 
                        "stack": "total", 
                        "itemStyle": {"color": "#B7E4C7"}, 
                        "data": incoming
                    },
                    {
                        "name": "Ausgaben (Standard)", 
                        "type": "bar", 
                        "stack": "total", 
                        "itemStyle": {"color": "#FFB3B3"}, 
                        "data": [-x for x in outgoing_standard]  # Negative Werte für die Darstellung
                    },
                    {
                        "name": "Ausgaben (Fixkosten)", 
                        "type": "bar", 
                        "stack": "total", 
                        "itemStyle": {"color": "#FFD580"}, 
                        "data": [-x for x in outgoing_fixkosten]  # Negative Werte für die Darstellung
                    },
                    {
                        "name": "Ausgaben (Simulation)", 
                        "type": "bar", 
                        "stack": "total", 
                        "itemStyle": {"color": "#C8A2C8"}, 
                        "data": [-x for x in outgoing_simulation]  # Negative Werte für die Darstellung
                    },
                    {
                        "name": "Ausgaben (Lohn)", 
                        "type": "bar", 
                        "stack": "total", 
                        "itemStyle": {"color": "#FFA07A"}, 
                        "data": [-x for x in outgoing_lohn]  # Negative Werte für die Darstellung
                    },
                    {
                        "name": "Kontostand", 
                        "type": "line", 
                        "smooth": True, 
                        "symbol": "circle", 
                        "symbolSize": 10,
                        "lineStyle": {"width": 3}, 
                        "itemStyle": {"color": "#6666CC"}, 
                        "data": kontostand
                    }
                ]
            }
            
            # Fokus auf die ersten 3 Monate für die Standardansicht
            if len(months) > 3:
                chart["dataZoom"][0]["end"] = int(3 / len(months) * 100)
                chart["dataZoom"][1]["end"] = int(3 / len(months) * 100)
            
            st_echarts(options=chart, height="500px")
        else:
            # Fallback ohne Kategorien
            monthly = df.groupby(["Monat", "Direction"])["Amount"].sum().unstack().fillna(0)
            months = monthly.index.tolist()
            incoming = monthly.get("Incoming", pd.Series(0, index=months)).tolist()
            outgoing = monthly.get("Outgoing", pd.Series(0, index=months)).tolist()
            kontostand = df.groupby("Monat")["Kontostand"].last().tolist()
            
            chart = {
                "tooltip": {"trigger": "axis"},
                "legend": {"data": ["Einnahmen", "Ausgaben", "Kontostand"]},
                "xAxis": {"type": "category", "data": months},
                "yAxis": {"type": "value"},
                "toolbox": {
                    "feature": {
                        "dataZoom": {"yAxisIndex": "none"},
                        "restore": {},
                        "saveAsImage": {}
                    }
                },
                "dataZoom": [
                    {"type": "inside", "start": 0, "end": 100},
                    {"start": 0, "end": 100}
                ],
                "series": [
                    {"name": "Einnahmen", "type": "bar", "stack": "total", "itemStyle": {"color": "#B7E4C7"}, "data": incoming},
                    {"name": "Ausgaben", "type": "bar", "stack": "total", "itemStyle": {"color": "#FFB3B3"}, "data": outgoing},
                    {"name": "Kontostand", "type": "line", "smooth": True, "symbol": "circle", "symbolSize": 10,
                     "lineStyle": {"width": 3}, "itemStyle": {"color": "#6666CC"}, "data": kontostand}
                ]
            }
            
            # Fokus auf die ersten 3 Monate für die Standardansicht
            if len(months) > 3:
                chart["dataZoom"][0]["end"] = int(3 / len(months) * 100)
                chart["dataZoom"][1]["end"] = int(3 / len(months) * 100)
                
            st_echarts(options=chart, height="500px")
    except Exception as e:
        st.error(f"Fehler bei der Monatsübersicht: {e}")
        st.info("Überspringe Monatsübersicht aufgrund von Datenstruktur-Problemen.")

    try:
        # Tagesverlauf
        st.subheader("📅 Tagesgenaue Liquiditätsentwicklung")
        
        # Erzeuge vollständige Tagesreihe für den ausgewählten Zeitraum
        if show_daily_points:
            date_range = pd.date_range(start=start_date, end=end_date, freq='D')
            daily_df = pd.DataFrame({'Date': date_range})
            
            # Kombiniere mit vorhandenen Daten
            df_temp = df.copy()
            df_temp["Date"] = pd.to_datetime(df_temp["Date"]).dt.date
            daily_sum = df_temp.groupby(df_temp["Date"])["Amount"].sum().reset_index()
            daily_sum["Date"] = pd.to_datetime(daily_sum["Date"])
            
            # Left join mit dem Datumsreihen-DataFrame
            daily_df = daily_df.merge(daily_sum, on="Date", how="left").fillna(0)
            
            # Kontostand berechnen
            daily_df["Amount_cumsum"] = daily_df["Amount"].cumsum()
            daily_df["Kontostand"] = daily_df["Amount_cumsum"] + start_balance
            
            # NaN-Werte mit dem zuletzt gültigen Wert füllen (FutureWarning behoben)
            daily_df["Kontostand"] = daily_df["Kontostand"].ffill().fillna(start_balance)
        else:
            # Nur Tage mit tatsächlichen Buchungen anzeigen
            df_daily = df.groupby("Date").agg({"Amount": "sum", "Kontostand": "last"}).reset_index()
            daily_df = df_daily.copy()
            
        daily_df["Datum"] = daily_df["Date"].dt.strftime("%Y-%m-%d")

        # Erweiterte Optionen für das Tagesdiagramm
        daily_chart = {
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": daily_df["Datum"].tolist(), "axisLabel": {"rotate": 45}},
            "yAxis": {"type": "value"},
            "toolbox": {
                "feature": {
                    "dataZoom": {"yAxisIndex": "none"},
                    "restore": {},
                    "saveAsImage": {}
                }
            },
            "dataZoom": [
                {"type": "inside", "start": 0, "end": 100},
                {"start": 0, "end": 100}
            ],
            "series": [
                {
                    "data": daily_df["Kontostand"].tolist(),
                    "type": "line",
                    "smooth": True,
                    "symbol": "circle",
                    "symbolSize": 6,
                    "lineStyle": {"width": 3, "color": "#4A90E2"},
                    "itemStyle": {"color": "#4A90E2"},
                    "areaStyle": {
                        "color": {
                            "type": "linear",
                            "x": 0, "y": 0, "x2": 0, "y2": 1,
                            "colorStops": [
                                {"offset": 0, "color": "#A0C4FF"},
                                {"offset": 1, "color": "rgba(160, 196, 255, 0.1)"}
                            ]
                        }
                    }
                }
            ]
        }
        
        # Fokus auf die ersten 90 Tage (3 Monate) für die Standardansicht
        total_days = len(daily_df["Datum"].tolist())
        if total_days > 90:
            daily_chart["dataZoom"][0]["end"] = int(90 / total_days * 100)
            daily_chart["dataZoom"][1]["end"] = int(90 / total_days * 100)
            
        st_echarts(options=daily_chart, height="500px")
    except Exception as e:
        st.error(f"Fehler bei der Tagesentwicklung: {e}")
        st.info("Überspringe Tagesentwicklung aufgrund von Datenstruktur-Problemen.")
    
    # Vollständig überarbeitete Fixkosten-Analyse
    if show_fixkosten:
        try:
            st.subheader("💼 Fixkosten-Analyse")
            
            # Direktes Laden der Fixkosten aus der Datenbank für eine bessere Analyse
            fixkosten_raw = load_fixkosten()
            
            if not fixkosten_raw.empty:
                # Spalten für die Anzeige vorbereiten
                fixkosten_display = []
                
                # Summen für verschiedene Rhythmen
                summe_monatlich = 0
                summe_quartalsweise = 0
                summe_halbjaehrlich = 0
                summe_jaehrlich = 0
                
                # Fixkosten nach Rhythmus gruppieren
                for _, fk in fixkosten_raw.iterrows():
                    # Nur aktive Fixkosten berücksichtigen
                    heute = pd.Timestamp(date.today())
                    if pd.isna(fk.get("enddatum")) or pd.to_datetime(fk["enddatum"]) > heute:
                        rhythmus = fk.get("rhythmus", "").lower()
                        betrag = float(fk["betrag"])
                        
                        # Je nach Rhythmus zur entsprechenden Summe addieren
                        if rhythmus == "monatlich":
                            summe_monatlich += betrag
                        elif rhythmus == "quartalsweise":
                            summe_quartalsweise += betrag / 3  # Pro Monat
                        elif rhythmus == "halbjährlich":
                            summe_halbjaehrlich += betrag / 6  # Pro Monat
                        elif rhythmus == "jährlich":
                            summe_jaehrlich += betrag / 12  # Pro Monat
                            
                        # Für die Anzeige vorbereiten
                        fixkosten_display.append({
                            "Name": fk.get("name", ""),
                            "Rhythmus": rhythmus.capitalize(),
                            "Betrag": betrag,
                            "Betrag_Monatlich": betrag if rhythmus == "monatlich" else (
                                betrag / 3 if rhythmus == "quartalsweise" else (
                                    betrag / 6 if rhythmus == "halbjährlich" else betrag / 12
                                )
                            )
                        })
                
                # DataFrame für die Anzeige erstellen
                if fixkosten_display:
                    df_fixkosten = pd.DataFrame(fixkosten_display)
                    df_fixkosten = df_fixkosten.sort_values(["Rhythmus", "Betrag"], ascending=[True, False])
                    
                    # Formatierte Beträge
                    df_fixkosten["Betrag_Anzeige"] = df_fixkosten["Betrag"].apply(lambda x: chf_format(x))
                    
                    # Anzeige der Fixkosten nach Rhythmus
                    st.markdown("#### Fixkosten nach Rhythmus")
                    st.dataframe(
                        df_fixkosten[["Name", "Rhythmus", "Betrag_Anzeige"]].rename(
                            columns={"Betrag_Anzeige": "Betrag"}
                        ),
                        use_container_width=True
                    )
                    
                    # Berechnung der monatlichen Gesamtbelastung
                    monatliche_summe = summe_monatlich + summe_quartalsweise + summe_halbjaehrlich + summe_jaehrlich
                    
                    st.markdown(f"**Monatliche Fixkosten-Gesamtbelastung: {chf_format(monatliche_summe)}**")
                    
                    # Pie-Chart der Fixkosten nach Rhythmus (mit monatlichen Anteilen)
                    pie_data = []
                    
                    if summe_monatlich > 0:
                        pie_data.append({"name": "Monatlich", "value": summe_monatlich})
                    
                    if summe_quartalsweise > 0:
                        pie_data.append({"name": "Quartalsweise (monatl. Anteil)", "value": summe_quartalsweise})
                        
                    if summe_halbjaehrlich > 0:
                        pie_data.append({"name": "Halbjährlich (monatl. Anteil)", "value": summe_halbjaehrlich})
                        
                    if summe_jaehrlich > 0:
                        pie_data.append({"name": "Jährlich (monatl. Anteil)", "value": summe_jaehrlich})
                    
                    pie_chart = {
                        "tooltip": {
                            "trigger": "item", 
                            "formatter": "{a} <br/>{b}: {c} CHF ({d}%)"
                        },
                        "legend": {
                            "orient": "vertical", 
                            "left": "left", 
                            "data": [item["name"] for item in pie_data]
                        },
                        "series": [
                            {
                                "name": "Fixkosten pro Monat",
                                "type": "pie",
                                "radius": ["30%", "70%"],
                                "avoidLabelOverlap": False,
                                "label": {
                                    "show": True,
                                    "formatter": "{b}: {c} CHF"
                                },
                                "emphasis": {
                                    "label": {
                                        "show": True,
                                        "fontSize": "18",
                                        "fontWeight": "bold"
                                    }
                                },
                                "labelLine": {"show": True},
                                "data": pie_data
                            }
                        ]
                    }
                    
                    st_echarts(options=pie_chart, height="400px")
                    
                    # Zusätzliche Fixkosten-Analyse für den ausgewählten Zeitraum
                    st.markdown("#### Monatliche Fixkosten-Übersicht")
                    
                    # Nach Kategorien
                    df_fixkosten["Kategorie"] = df_fixkosten["Name"].apply(
                        lambda x: "Miete" if "miete" in x.lower() else (
                            "Lizenzen" if "lizenz" in x.lower() else (
                                "IT-Kosten" if any(k in x.lower() for k in ["it", "cloud", "software", "hardware"]) else "Sonstiges"
                            )
                        )
                    )
                    
                    # Gruppiert nach Kategorie
                    category_sum = df_fixkosten.groupby("Kategorie")["Betrag_Monatlich"].sum().reset_index()
                    
                    # Balkendiagramm der Fixkosten nach Kategorie
                    bar_data = [{"name": row["Kategorie"], "value": row["Betrag_Monatlich"]} for _, row in category_sum.iterrows()]
                    
                    bar_chart = {
                        "tooltip": {"trigger": "axis"},
                        "xAxis": {
                            "type": "category",
                            "data": [item["name"] for item in bar_data]
                        },
                        "yAxis": {"type": "value"},
                        "series": [
                            {
                                "name": "Monatliche Kosten",
                                "type": "bar",
                                "data": [item["value"] for item in bar_data],
                                "itemStyle": {"color": "#91CC75"}
                            }
                        ]
                    }
                    
                    st_echarts(options=bar_chart, height="300px")

                else:
                    st.info("Keine aktiven Fixkosten gefunden.")
            else:
                st.info("Keine Fixkosten-Daten vorhanden.")
                
        except Exception as e:
            st.error(f"Fehler bei der Fixkosten-Analyse: {e}")
            st.info("Überspringe Fixkosten-Analyse aufgrund von Datenstruktur-Problemen.")
            
    # Lohnkosten-Analyse (falls aktiviert)
    if show_loehne:
        try:
            st.subheader("💰 Lohnkosten-Analyse")
            
            # Aktuelle Lohndaten abrufen
            aktuelle_loehne = get_aktuelle_loehne()
            
            if aktuelle_loehne:
                # Für die Anzeige vorbereiten
                df_loehne = pd.DataFrame(aktuelle_loehne)
                
                # Formatierung für die Anzeige
                df_loehne["Betrag_Anzeige"] = df_loehne["Betrag"].apply(lambda x: chf_format(x))
                
                # Monatliche Gesamtsumme berechnen
                summe_monatlich = sum(float(lohn["Betrag"]) for lohn in aktuelle_loehne)
                
                # Anzeige der aktuellen Lohnkosten
                st.markdown("#### Aktuelle Lohnkosten")
                st.dataframe(
                    df_loehne[["Mitarbeiter", "Betrag_Anzeige"]].rename(
                        columns={"Betrag_Anzeige": "Lohn"}
                    ),
                    use_container_width=True
                )
                
                st.markdown(f"**Monatliche Lohnkosten-Gesamtbelastung: {chf_format(summe_monatlich)}**")
                st.markdown(f"**Auszahlung erfolgt am 25. des Monats**")
                
                # Balkendiagramm der Löhne pro Mitarbeiter
                bar_data = [{"name": row["Mitarbeiter"], "value": row["Betrag"]} for _, row in df_loehne.iterrows()]
                
                bar_chart = {
                    "tooltip": {"trigger": "axis"},
                    "xAxis": {
                        "type": "category",
                        "data": [item["name"] for item in bar_data]
                    },
                    "yAxis": {"type": "value"},
                    "series": [
                        {
                            "name": "Monatlicher Lohn",
                            "type": "bar",
                            "data": [item["value"] for item in bar_data],
                            "itemStyle": {"color": "#5470C6"}
                        }
                    ]
                }
                
                st_echarts(options=bar_chart, height="300px")
                
                # Prozentuale Verteilung anzeigen
                st.markdown("#### Lohnverteilung")
                
                # Pie-Chart für die Lohnverteilung
                pie_data = [{"name": row["Mitarbeiter"], "value": row["Betrag"]} for _, row in df_loehne.iterrows()]
                
                pie_chart = {
                    "tooltip": {
                        "trigger": "item", 
                        "formatter": "{a} <br/>{b}: {c} CHF ({d}%)"
                    },
                    "legend": {
                        "orient": "vertical", 
                        "left": "left", 
                        "data": [item["name"] for item in pie_data]
                    },
                    "series": [
                        {
                            "name": "Lohnverteilung",
                            "type": "pie",
                            "radius": ["30%", "70%"],
                            "avoidLabelOverlap": False,
                            "label": {
                                "show": True,
                                "formatter": "{b}: {c} CHF ({d}%)"
                            },
                            "emphasis": {
                                "label": {
                                    "show": True,
                                    "fontSize": "18",
                                    "fontWeight": "bold"
                                }
                            },
                            "labelLine": {"show": True},
                            "data": pie_data
                        }
                    ]
                }
                
                st_echarts(options=pie_chart, height="400px")
            else:
                st.info("Keine aktuellen Lohndaten verfügbar.")
        except Exception as e:
            st.error(f"Fehler bei der Lohnkosten-Analyse: {e}")
            st.info("Überspringe Lohnkosten-Analyse aufgrund von Datenstruktur-Problemen.")

    # Session-State für die Single-Open Expander Funktionalität
    if "open_expander" not in st.session_state:
        st.session_state.open_expander = None