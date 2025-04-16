import streamlit as st
from streamlit_option_menu import option_menu
import base64
from core.utils import load_svg_logo
from core.utils import chf_format
from views import datenimport, planung, editor, analyse, simulation, fixkosten, mitarbeiter, reset, login, admin
from datetime import date, timedelta
from core.auth import initialisiere_auth_state, prüfe_session_gültigkeit, log_user_activity

# ----------------------------------
# 📱 App-Einstellungen
# ----------------------------------
st.set_page_config(
    layout="wide", 
    initial_sidebar_state="expanded",
    page_title="vaios Liq-Planung"
)

# Authentifizierungsstatus initialisieren
initialisiere_auth_state()

# Dynamische CSS-Anpassungen basierend auf Benutzereinstellungen
def apply_custom_styles():
    primary_color = st.session_state.design_settings.get("primary_color", "#4A90E2")
    secondary_color = st.session_state.design_settings.get("secondary_color", "#111")
    background_color = st.session_state.design_settings.get("background_color", "#FFFFFF")
    
    st.markdown(f"""
    <style>
        /* Bessere Margins für den Seiteninhalt */
        .main .block-container {{
            padding-top: 2rem;
            margin-top: 0;
        }}
        
        /* Streamlit-Standardränder reduzieren */
        .stApp > header {{
            background-color: transparent;
        }}
        
        /* Verbesserte Darstellung von Elementen */
        div.stButton > button {{
            width: 100%;
        }}
        
        /* Optisches Trennen von Hauptbereichen */
        .main .element-container {{
            margin-bottom: 1rem;
        }}
        
        /* Verbessern der DataFrame-Darstellung */
        div[data-testid="stDataFrame"] table {{
            border-collapse: separate;
            border-spacing: 0;
            border-radius: 5px;
        }}
        
        /* Formatierung für CHF-Inputs */
        input[data-testid="stTextInput"] {{
            text-align: right;
        }}
        
        /* Benutzerdefinierte Farbeinstellungen */
        .stApp {{
            background-color: {background_color};
        }}
        
        .nav-link-selected {{
            background-color: {primary_color} !important;
        }}
        
        div.stButton > button:first-child {{
            background-color: {primary_color};
            color: white;
        }}
        
        div.stButton > button:hover {{
            background-color: {primary_color};
            color: white;
            opacity: 0.8;
        }}
        
        .css-1offfwp {{  /* InfoBarContainer */
            color: {secondary_color};
        }}
        
        div.stMarkdown h1, div.stMarkdown h2, div.stMarkdown h3 {{
            color: {secondary_color};
        }}
    </style>
    """, unsafe_allow_html=True)

# Anwenden der benutzerdefinierten Stile
apply_custom_styles()

# ----------------------------------
# Logo in der Seitenleiste
# ----------------------------------
with st.sidebar:
    st.sidebar.image(load_svg_logo('assets/vaios-logo.svg'), width=150)
    st.sidebar.title("Liq-Planung")

    # Benutzerinformationen anzeigen, wenn angemeldet
    if st.session_state.is_authenticated and st.session_state.user:
        st.sidebar.success(f"Angemeldet als: {st.session_state.user.email}")
        if st.session_state.is_admin:
            st.sidebar.info("Administrator")
        # Read-Only Status anzeigen
        from core.auth import is_read_only
        if is_read_only():
            st.sidebar.warning("Lesezugriff (Read-Only)")

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
# Optionen für die Navigation basierend auf Authentifizierungsstatus
if st.session_state.is_authenticated:
    # Navigationselemente für angemeldete Benutzer
    nav_options = ["Start", "Datenimport", "Planung", "Editor", "Analyse", "Simulation", "Fixkosten", "Mitarbeiter"]
    nav_icons = ["house", "cloud-upload", "journal-check", "pencil-square", "bar-chart-line", "lightning", "wallet2", "people"]
    
    # Admin-Element hinzufügen, wenn der Benutzer Admin-Rechte hat
    if st.session_state.is_admin:
        nav_options.append("Admin")
        nav_icons.append("gear")
    
    # Abmelden-Element am Ende hinzufügen
    nav_options.append("Abmelden")
    nav_icons.append("box-arrow-right")
else:
    # Navigationselemente für nicht angemeldete Benutzer
    nav_options = ["Login"]
    nav_icons = ["key"]

# WICHTIG: Konvertiere Listen zu Listen (nicht zu Sets), um JSON-Serialisierungsprobleme zu vermeiden
nav_options = list(nav_options)
nav_icons = list(nav_icons)

# Navigationselement definieren
selected = option_menu(
    menu_title=None,
    options=nav_options,
    icons=nav_icons,
    orientation="horizontal",
    default_index=0 if selected_tab is None else nav_options.index(selected_tab) if selected_tab in nav_options else 0,
    styles={
        "container": {"padding": "0!important", "width": "100%", "margin": "0 0 1rem 0"},
        "icon": {"color": "#111", "font-size": "14px"},
        "nav-link": {"font-size": "14px", "text-align": "center", "margin": "0px", "--hover-color": "#eee", "padding": "10px 15px"},
        "nav-link-selected": {"background-color": st.session_state.design_settings.get("primary_color", "#4A90E2"), "color": "white"},
    }
)

# ----------------------------------
# Kontostand-Einstellung (global verfügbar, nur für angemeldete Benutzer)
# ----------------------------------
if st.session_state.is_authenticated:
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
                
                # Aktivität protokollieren
                log_user_activity("Kontostand aktualisiert", {"new_value": new_value})
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
        
        # Prüfen, ob Benutzer im Read-Only Modus ist
        from core.auth import is_read_only
        readonly_mode = is_read_only()
        
        # Kontostand direkt als Textfeld
        text_input = st.text_input(
            "Kontostand (CHF):",
            value=st.session_state.kontostand_direkt,
            key="kontostand_direkt",
            on_change=update_kontostand,
            disabled=readonly_mode  # Deaktivieren, wenn Read-Only
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

# Wenn nicht authentifiziert und nicht auf der Login-Seite, zur Login-Seite weiterleiten
if not st.session_state.is_authenticated and selected != "Login":
    st.info("Bitte melden Sie sich an, um auf die App zuzugreifen")
    login.show()
    st.stop()

# Navigation für authentifizierte Benutzer
if selected == "Login":
    login.show()
elif selected == "Abmelden":
    from core.auth import abmelden
    abmelden()
    st.rerun()
elif selected == "Start":
    # Startseite - nur anzeigen, wenn authentifiziert
    if st.session_state.is_authenticated:
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
elif selected == "Datenimport":
    if prüfe_session_gültigkeit():
        datenimport.show()
elif selected == "Planung":
    if prüfe_session_gültigkeit():
        planung.show()
elif selected == "Editor":
    if prüfe_session_gültigkeit():
        editor.show()
elif selected == "Analyse":
    if prüfe_session_gültigkeit():
        analyse.show()
elif selected == "Simulation":
    if prüfe_session_gültigkeit():
        simulation.show()
elif selected == "Fixkosten":
    if prüfe_session_gültigkeit():
        fixkosten.show()
elif selected == "Mitarbeiter":
    if prüfe_session_gültigkeit():
        mitarbeiter.show()
elif selected == "Admin":
    if prüfe_session_gültigkeit() and st.session_state.is_admin:
        admin.show()
    else:
        st.error("Sie haben keine Berechtigung, auf diesen Bereich zuzugreifen")
        
# ----------------------------------
# 👤 Footer
# ----------------------------------
st.markdown("""
<div style="position: fixed; bottom: 0; right: 0; padding: 10px; background-color: rgba(255,255,255,0.7); border-radius: 5px; margin: 10px; font-size: 12px;">
    <a href="https://www.vaios.ch" target="_blank" style="color: #666; text-decoration: none;">© vaios GmbH</a>
</div>
""", unsafe_allow_html=True)