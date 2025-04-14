import streamlit as st
from streamlit_option_menu import option_menu
import base64
from core.utils import load_svg_logo
from core.utils import chf_format
from views import datenimport, planung, editor, analyse, simulation, fixkosten, mitarbeiter, reset
from datetime import date, timedelta

# ----------------------------------
# 📱 App-Einstellungen
# ----------------------------------
st.set_page_config(
    layout="wide", 
    initial_sidebar_state="expanded",
    page_title="vaios Liq-Planung"
)

# Einfacherer Ansatz für die CSS-Anpassungen
st.markdown("""
<style>
    /* Bessere Margins für den Seiteninhalt */
    .main .block-container {
        padding-top: 2rem;
        margin-top: 0;
    }
    
    /* Streamlit-Standardränder reduzieren */
    .stApp > header {
        background-color: transparent;
    }
    
    /* Verbesserte Darstellung von Elementen */
    div.stButton > button {
        width: 100%;
    }
    
    /* Optisches Trennen von Hauptbereichen */
    .main .element-container {
        margin-bottom: 1rem;
    }
    
    /* Verbessern der DataFrame-Darstellung */
    div[data-testid="stDataFrame"] table {
        border-collapse: separate;
        border-spacing: 0;
        border-radius: 5px;
    }
    
    /* Formatierung für CHF-Inputs */
    input[data-testid="stTextInput"] {
        text-align: right;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------------
# Logo in der Seitenleiste
# ----------------------------------
with st.sidebar:
    st.sidebar.image(load_svg_logo('assets/vaios-logo.svg'), width=150)
    st.sidebar.title("Liq-Planung")

# ----------------------------------
# Kontostand-Initialisierung
# ----------------------------------
if "start_balance" not in st.session_state:
    st.session_state.start_balance = 0

# Behandlung der Navigation über Buttons
# Prüfe, ob die Navigation durch einen Schnellstart-Button ausgelöst wurde
if "go_to_planung" in st.session_state and st.session_state.go_to_planung:
    selected_tab = "Planung"
    st.session_state.go_to_planung = False
elif "go_to_analyse" in st.session_state and st.session_state.go_to_analyse:
    selected_tab = "Analyse"
    st.session_state.go_to_analyse = False
else:
    selected_tab = None  # Kein Tab durch Knopfdruck gewählt

# ----------------------------------
# 🧭 Navigation
# ----------------------------------
selected = option_menu(
    menu_title=None,
    options=["Start", "Datenimport", "Planung", "Editor", "Analyse", "Simulation", "Fixkosten", "Mitarbeiter", "Zurücksetzen"],
    icons=["house", "cloud-upload", "journal-check", "pencil-square", "bar-chart-line", "lightning", "wallet2", "people", "arrow-counterclockwise"],
    orientation="horizontal",
    default_index=0 if selected_tab is None else ["Start", "Datenimport", "Planung", "Editor", "Analyse", "Simulation", "Fixkosten", "Mitarbeiter", "Zurücksetzen"].index(selected_tab),
    styles={
        "container": {"padding": "0!important", "width": "100%", "margin": "0 0 1rem 0"},
        "icon": {"color": "#111", "font-size": "14px"},
        "nav-link": {"font-size": "14px", "text-align": "center", "margin": "0px", "--hover-color": "#eee", "padding": "10px 15px"},
        "nav-link-selected": {"background-color": "#4A90E2", "color": "white"},
    }
)


# ----------------------------------
# Kontostand-Einstellung (global verfügbar)
# ----------------------------------
with st.sidebar:
    st.sidebar.subheader("💰 Kontostand")
    
    # Funktion zum Aktualisieren des Kontostands
    def update_kontostand():
        try:
            # Format bereinigen
            clean_input = st.session_state.kontostand_direkt.replace("'", "").replace(",", ".")
            if clean_input.startswith("CHF"):
                clean_input = clean_input[3:].strip()  # "CHF " am Anfang entfernen
            
            # In Zahl umwandeln
            new_value = float(clean_input)
            st.session_state.start_balance = new_value
            st.session_state.kontostand_direkt = chf_format(new_value)  # Formatieren nach Änderung
            st.session_state.kontostand_changed = True
        except:
            st.session_state.kontostand_direkt = chf_format(st.session_state.start_balance)  # Bei Fehler zurücksetzen
            st.session_state.kontostand_error = True
    
    # Initialisierung
    if "kontostand_direkt" not in st.session_state:
        st.session_state.kontostand_direkt = chf_format(st.session_state.start_balance)
    
    if "kontostand_changed" not in st.session_state:
        st.session_state.kontostand_changed = False
    
    if "kontostand_error" not in st.session_state:
        st.session_state.kontostand_error = False
    
    # Kontostand direkt als Textfeld
    text_input = st.text_input(
        "Kontostand (CHF):",
        value=st.session_state.kontostand_direkt,
        key="kontostand_direkt",
        on_change=update_kontostand
    )
    
    # Erfolgsmeldung nach Änderung
    if st.session_state.kontostand_changed:
        st.success(f"Kontostand aktualisiert auf {chf_format(st.session_state.start_balance)}")
        st.session_state.kontostand_changed = False  # Zurücksetzen für nächste Änderung
    
    # Fehlermeldung
    if st.session_state.kontostand_error:
        st.error("Bitte gib einen gültigen Betrag ein")
        st.session_state.kontostand_error = False  # Zurücksetzen


# ----------------------------------
# 📂 Views laden
# ----------------------------------
if selected == "Start":
    # Neuer Startscreen
    st.title("Willkommen bei vaios Liq-Planung")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### Finanzübersicht
        
        Mit dieser App verwaltest du deine Liquiditätsplanung einfach und effizient:
        
        - **Unternehmensfinanzen** übersichtlich darstellen
        - **Fixkosten** und **Simulationen** verwalten
        - **Mitarbeiter** und Lohnkosten im Blick behalten
        - **Analysen** zur Liquiditätsplanung erstellen
        
        Nutze das Menü oben, um zwischen den verschiedenen Bereichen zu wechseln.
        """)
        
        # Quickstart Buttons
        st.subheader("Schnellstart")
        quickstart_col1, quickstart_col2 = st.columns(2)
        with quickstart_col1:
            # Verbesserte Button-Funktionalität
            if st.button("➡️ Zur Planung", use_container_width=True):
                st.session_state.go_to_planung = True
                st.rerun()
                
        with quickstart_col2:
            # Verbesserte Button-Funktionalität
            if st.button("📊 Zur Analyse", use_container_width=True):
                st.session_state.go_to_analyse = True
                st.rerun()
    
    with col2:
        # Status-Übersicht
        st.markdown("### Status")
        
        # Aktuelles Datum
        st.info(f"**Datum:** {date.today().strftime('%d.%m.%Y')}")
        
        # Kontostand
        st.success(f"**Aktueller Kontostand:** {chf_format(st.session_state.start_balance)}")
        
        # Planungshorizont
        today = date.today()
        default_end = today + timedelta(days=270)  # 9 Monate
        st.info(f"**Standardplanungszeitraum:** {today.strftime('%d.%m.%Y')} bis {default_end.strftime('%d.%m.%Y')}")
        
        # Weitere hilfreiche Informationen
        st.subheader("Tipps")
        st.markdown("""
        - Beginne mit dem **Datenimport**, um deine Daten zu laden
        - Verwalte deine **Fixkosten** und **Mitarbeiter**
        - Erstelle **Simulationen** für verschiedene Szenarien
        - Visualisiere Ergebnisse in der **Analyse**
        """)
    
if selected == "Datenimport":
    datenimport.show()

elif selected == "Planung":
    planung.show()

elif selected == "Editor":
    editor.show()

elif selected == "Analyse":
    analyse.show()

elif selected == "Simulation":
    simulation.show()

elif selected == "Fixkosten":
    fixkosten.show()

elif selected == "Mitarbeiter":
    mitarbeiter.show()
    
elif selected == "Zurücksetzen":
    reset.show()


# ----------------------------------
# 👤 Footer
# ----------------------------------
st.markdown("""
<div style="position: fixed; bottom: 0; right: 0; padding: 10px; background-color: rgba(255,255,255,0.7); border-radius: 5px; margin: 10px; font-size: 12px;">
    <a href="https://www.vaios.ch" target="_blank" style="color: #666; text-decoration: none;">© vaios GmbH</a>
</div>
""", unsafe_allow_html=True)