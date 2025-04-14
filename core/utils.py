import base64
import re

# ----------------------------------
# 🪐 CHF-Beträge schön formatieren
# ----------------------------------
def chf_format(x):
    """Formatiert einen numerischen Wert als CHF-Betrag."""
    try:
        return f"CHF {x:,.2f}".replace(",", "'")
    except:
        return x

# ----------------------------------
# 🪐 CHF-Beträge für Eingabefelder parsen
# ----------------------------------
def parse_chf_input(input_str):
    """
    Wandelt einen CHF-Betrag in der Eingabe in eine Zahl um.
    Akzeptiert verschiedene Eingabeformate wie:
    - 1'000.00
    - 1,000.00
    - CHF 1'000.00
    - 1000
    - 1000.0
    """
    try:
        # Wenn leer, gib 0 zurück
        if not input_str or input_str.strip() == "":
            return 0.0
            
        # Entferne "CHF" Prefix, wenn vorhanden
        cleaned = input_str.strip()
        if cleaned.upper().startswith("CHF"):
            cleaned = cleaned[3:].strip()
        
        # Ersetze Tausendertrennzeichen und Komma durch Punkt
        cleaned = cleaned.replace("'", "").replace(",", ".")
        
        # Entferne alle Nicht-Zahlen außer Punkt
        cleaned = re.sub(r"[^\d.]", "", cleaned)
        
        # In Zahl umwandeln
        return float(cleaned)
    except:
        # Bei Fehler gib None zurück
        return None

# ----------------------------------
# 🪐 CHF-Input für Text-Felder formatieren
# ----------------------------------
def format_chf_input_while_typing(input_str):
    """
    Formatiert einen CHF-Betrag während der Eingabe.
    Wird für Callbacks bei Texteingabefeldern verwendet.
    """
    try:
        # Wenn leer, nix zurückgeben
        if not input_str or input_str.strip() == "":
            return ""
            
        # Nur Zahlen und bestimmte Zeichen erlauben
        digits_only = re.sub(r"[^\d,'.]", "", input_str)
        
        # Entferne alle Tausendertrennzeichen und Kommas
        cleaned = digits_only.replace("'", "").replace(",", ".")
        
        # Prüfe, ob es sich um eine gültige Zahl handelt
        value = float(cleaned)
        
        # Formatiere die Zahl
        formatted = f"{value:,.2f}".replace(",", "'")
        
        # Füge CHF hinzu, wenn es nicht schon da ist
        if not input_str.strip().upper().startswith("CHF"):
            return f"CHF {formatted}"
        else:
            return f"CHF {formatted}"
    except:
        # Bei Fehler gib die Eingabe unverändert zurück
        return input_str

# ----------------------------------
# 🖼️ Firmenlogo einbetten
# ----------------------------------
def load_svg_logo(path):
    """Lädt ein SVG-Logo und gibt es als Base64-encoded Data-URL zurück."""
    with open(path, "rb") as f:
        svg = f.read()
    b64_svg = base64.b64encode(svg).decode("utf-8")
    return f"data:image/svg+xml;base64,{b64_svg}"