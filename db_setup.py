import streamlit as st
from core.storage import supabase
import os
def setup_database():
    """
    Skript zum Einrichten der Datenbank-Tabellen und RLS-Richtlinien in Supabase
    """
    print("Tabellen wurden bereits in Supabase erstellt.")
    return True

def create_admin_user(email, password, name):
    """
    Erstellt einen ersten Admin-Benutzer
    """
    try:
        # Benutzer erstellen
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        
        if response.user:
            user_id = response.user.id
            
            # Admin-Profil erstellen
            profile_data = {
                "id": user_id,
                "name": name,
                "role": "admin"
            }
            
            supabase.table('profiles').insert(profile_data).execute()
            
            print(f"Admin-Benutzer {email} erfolgreich erstellt.")
            return True
    except Exception as e:
        print(f"Fehler beim Erstellen des Admin-Benutzers: {str(e)}")
    
    return False