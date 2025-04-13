from core.storage import supabase

def delete_all_rows(table_name: str):
    """Löscht alle Zeilen aus der Tabelle, bei denen eine gültige UUID vorhanden ist."""
    try:
        # Hole alle IDs
        response = supabase.table(table_name).select("id").execute()
        ids = [row["id"] for row in response.data if row.get("id") not in [None, "", "null"]]

        if ids:
            supabase.table(table_name).delete().in_("id", ids).execute()
    except Exception as e:
        print(f"⚠️ Fehler beim Löschen aus {table_name}: {e}")

def reset_all_data():
    """Setzt die App zurück (löscht alle dynamischen Tabellen)."""
    delete_all_rows("buchungen")
    delete_all_rows("fixkosten")
    delete_all_rows("mitarbeiter")
    delete_all_rows("simulationen")
