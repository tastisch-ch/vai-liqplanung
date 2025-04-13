import streamlit as st
from streamlit_option_menu import option_menu
import base64
from core.utils import load_svg_logo
from core.utils import chf_format
from views import datenimport, planung, editor, analyse, simulation, fixkosten, mitarbeiter, reset


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

# ----------------------------------
# 🧭 Navigation
# ----------------------------------
selected = option_menu(
    menu_title=None,
    options=["Datenimport", "Planung", "Editor", "Analyse", "Simulation", "Fixkosten", "Mitarbeiter", "Zurücksetzen"],
    icons=["cloud-upload", "journal-check", "pencil-square", "bar-chart-line", "lightning", "wallet2", "people", "arrow-counterclockwise"],
    orientation="horizontal",
    default_index=0,
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
    
    # Aktueller Kontostand anzeigen
    st.info(f"Aktueller Startkontostand: {chf_format(st.session_state.start_balance)}")
    
    # Session-State für Kontostand-Formular
    if "kontostand_error" not in st.session_state:
        st.session_state.kontostand_error = False
    if "kontostand_success" not in st.session_state:
        st.session_state.kontostand_success = False
    
    # Kontostand manuell setzen
    with st.expander("Kontostand manuell setzen"):
        # Bei Erfolg die Erfolgsmeldung anzeigen und Input zurücksetzen
        if st.session_state.kontostand_success:
            st.success(f"✅ Kontostand auf {chf_format(st.session_state.start_balance)} gesetzt")
            kontostand_input = ""  # Feld leeren nach Erfolg
        else:
            kontostand_input = st.text_input(
                "Kontostand (CHF)", 
                value="",
                placeholder="z.B. 12'000.00",
                key="kontostand_input"
            )
        
        # Bei Fehler die Fehlermeldung anzeigen
        if st.session_state.kontostand_error:
            st.error("❌ Bitte gebe einen gültigen Betrag ein")
        
        # Funktion für den Button-Klick
        def set_kontostand():
            try:
                # Formatierung entfernen und in Float umwandeln
                kontostand_clean = st.session_state.kontostand_input.replace("'", "").replace(",", ".")
                new_balance = float(kontostand_clean)
                
                # Kontostand setzen
                st.session_state.start_balance = new_balance
                
                # Erfolgsstatus setzen
                st.session_state.kontostand_success = True
                st.session_state.kontostand_error = False
                
                # Input zurücksetzen
                st.session_state.kontostand_input = ""
                
            except:
                # Fehlerstatus setzen
                st.session_state.kontostand_error = True
                st.session_state.kontostand_success = False
        
        # Button mit on_click Handler
        st.button("Kontostand setzen", on_click=set_kontostand, key="kontostand_button")


# ----------------------------------
# 📂 Views laden
# ----------------------------------
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