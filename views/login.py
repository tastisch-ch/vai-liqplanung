import streamlit as st
from core.auth import anmelden, abmelden, initialisiere_auth_state, prüfe_session_gültigkeit, passwort_zuruecksetzen

# Magic Link Funktion in core/auth.py hinzufügen
def magic_link_anmelden(email):
    """
    Sendet einen Magic Link zur angegebenen E-Mail-Adresse.
    
    Args:
        email (str): E-Mail-Adresse des Benutzers
        
    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    try:
        # Supabase Magic Link senden
        from core.storage import supabase
        response = supabase.auth.sign_in_with_otp({
            "email": email
        })
        
        if response:
            st.session_state.auth_message = f"Ein Magic Link wurde an {email} gesendet. Bitte prüfe deine E-Mails."
            st.session_state.auth_message_type = "info"
            return True
    except Exception as e:
        st.session_state.auth_message = f"Fehler beim Senden des Magic Links: {str(e)}"
        st.session_state.auth_message_type = "error"
    
    return False

def show():
    """
    Login-Seite anzeigen
    """
    # Authentifizierungsstatus initialisieren
    initialisiere_auth_state()
    
    # Prüfen, ob die Session noch gültig ist
    if st.session_state.is_authenticated:
        prüfe_session_gültigkeit()
    
    st.title("🔐 Login")
    
    # Statusmeldungen anzeigen (falls vorhanden)
    if st.session_state.auth_message:
        message_type = st.session_state.auth_message_type
        message = st.session_state.auth_message
        
        if message_type == "success":
            st.success(message)
        elif message_type == "error":
            st.error(message)
        elif message_type == "info":
            st.info(message)
        elif message_type == "warning":
            st.warning(message)
            
        # Nachricht zurücksetzen
        st.session_state.auth_message = None
        st.session_state.auth_message_type = None
    
    # Wenn bereits angemeldet, Abmelde-UI anzeigen
    if st.session_state.is_authenticated and st.session_state.user:
        logged_in_ui()
    else:
        # Tabs für verschiedene Login-Methoden
        tab1, tab2 = st.tabs(["Login mit Passwort", "Login mit Magic Link"])
        
        with tab1:
            login_form()
        
        with tab2:
            magic_link_form()
        
        # Passwort vergessen Link
        st.markdown("---")
        forgot_password()

def login_form():
    """
    Login-Formular darstellen
    """
    with st.form(key="login_form"):
        email = st.text_input(
            "E-Mail-Adresse",
            placeholder="name@beispiel.ch",
            help="Geben Sie Ihre E-Mail-Adresse ein"
        )
        
        password = st.text_input(
            "Passwort",
            type="password",
            placeholder="Passwort",
            help="Geben Sie Ihr Passwort ein"
        )
        
        stay_logged_in = st.checkbox(
            "Angemeldet bleiben",
            help="Aktivieren Sie diese Option, um für längere Zeit angemeldet zu bleiben"
        )
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            submit_button = st.form_submit_button(
                label="Anmelden",
                use_container_width=True
            )
            
        # Wenn das Formular abgeschickt wurde
        if submit_button:
            if not email or not password:
                st.error("Bitte geben Sie E-Mail und Passwort ein")
            else:
                with st.spinner("Anmeldung läuft..."):
                    anmelden(email, password, stay_logged_in)
                    # Seite neu laden, um die Änderungen zu übernehmen
                    st.rerun()

def magic_link_form():
    """
    Magic Link Login-Formular darstellen
    """
    st.markdown("""
    ### Login mit Magic Link
    Erhalte einen einmaligen Login-Link per E-Mail. Kein Passwort notwendig!
    """)
    
    with st.form(key="magic_link_form"):
        email = st.text_input(
            "E-Mail-Adresse",
            placeholder="name@beispiel.ch",
            help="Geben Sie Ihre registrierte E-Mail-Adresse ein"
        )
        
        submit_button = st.form_submit_button(
            label="Magic Link senden",
            use_container_width=True
        )
        
        if submit_button:
            if not email:
                st.error("Bitte geben Sie Ihre E-Mail-Adresse ein")
            else:
                with st.spinner("Magic Link wird gesendet..."):
                    magic_link_anmelden(email)

def logged_in_ui():
    """
    UI für angemeldete Benutzer
    """
    user = st.session_state.user
    
    st.success(f"Sie sind angemeldet als: {user.email}")
    
    if st.session_state.is_admin:
        st.info("Sie haben Administratorrechte")
    
    if st.button("Abmelden", use_container_width=True):
        abmelden()
        st.rerun()

def forgot_password():
    """
    Passwort vergessen Funktion
    """
    st.subheader("Passwort vergessen?")
    
    with st.form(key="reset_form"):
        email = st.text_input(
            "E-Mail-Adresse",
            placeholder="name@beispiel.ch",
            help="Geben Sie Ihre E-Mail-Adresse ein"
        )
        
        reset_button = st.form_submit_button(
            label="Passwort zurücksetzen",
            use_container_width=True
        )
        
        if reset_button:
            if not email:
                st.error("Bitte geben Sie Ihre E-Mail-Adresse ein")
            else:
                with st.spinner("E-Mail wird gesendet..."):
                    passwort_zuruecksetzen(email)