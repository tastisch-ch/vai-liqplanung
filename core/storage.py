import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

print("🔐 Geladener SUPABASE_KEY beginnt mit:", SUPABASE_KEY[:15])  # Das reicht für Kontrolle

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)