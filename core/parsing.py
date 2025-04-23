import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime

# ----------------------------------
# 👥 Liste der zu ignorierenden Empfänger (Mitarbeiter)
# ----------------------------------
# Hier kannst du die Namen von Mitarbeitern eintragen, deren Zahlungen beim Import ignoriert werden sollen
IGNORE_RECIPIENTS = [
    "Christoph Richard",
    "Alexandra Hürbin",
    "Darko Todic",
    "Carmen Ryser",
    "Guido Parpan",
    "Jana Trösch",
    "Nina Flückiger",
    "Werner Hügi",
    # weitere Namen hier ergänzen...
]

# ----------------------------------
# 🧠 Datum robust parsen (CH-Format)
# ----------------------------------
def parse_date_swiss_fallback(date_str):
    if isinstance(date_str, (pd.Timestamp, datetime)):
        return date_str

    date_str = str(date_str).strip()

    try:
        # Falls im ISO-Format (z. B. aus Supabase) (YYYY-MM-DD)
        if "-" in date_str:
            return pd.to_datetime(date_str, format="%Y-%m-%d", errors="coerce")
        elif "." in date_str:
            # CH-Format (DD.MM.YYYY)
            parts = date_str.split(".")
            if len(parts) == 3:
                day, month, year = parts
                day = day.zfill(2)
                month = month.zfill(2)
                if len(year) == 2:
                    year = "20" + year
                clean_str = f"{day}.{month}.{year}"
                return pd.to_datetime(clean_str, format="%d.%m.%Y", errors="coerce")
    except Exception:
        pass

    # Fallback für alle anderen Formate
    return pd.to_datetime(date_str, dayfirst=True, errors="coerce")


# ----------------------------------
# 🦡 HTML-Daten importieren & parsen
# ----------------------------------
def parse_html_output(html_string):
    """
    Parst HTML-Daten aus E-Banking für den Import mit robuster Fehlerbehandlung.
    """
    import re
    
    # Überprüfung auf leere Eingabe
    if not html_string or html_string.strip() == "":
        return pd.DataFrame(columns=['Date', 'Type', 'Details', 'Amount', 'Currency', 'Balance'])
        
    soup = BeautifulSoup(html_string, 'html.parser')
    rows = soup.find_all('tr')
    data = []
    
    for row in rows:
        try:
            cells = row.find_all('td')
            if not cells or len(cells) < 6:
                continue

            # Robust gegenüber verschiedenen HTML-Strukturen für das Datum
            date_span = cells[0].find('span', class_='print')
            if date_span:
                date_str = date_span.text.strip()
            else:
                # Fallback: direkter Text oder andere Strukturen
                date_str = cells[0].text.strip()
                
            date = parse_date_swiss_fallback(date_str)
            
            # Transaktionstyp
            type = cells[1].text.strip()
            if type == "Dauerauftrag":
                continue  # Ignoriere Daueraufträge
                
            # Details (verschiedene Strukturen behandeln)
            details_span = cells[2].find('span', class_='text')
            if details_span:
                details = details_span.text.strip()
            else:
                details = cells[2].text.strip()
                
            # Prüfe, ob der Empfänger in der Ignore-Liste ist
            should_ignore = False
            for recipient in IGNORE_RECIPIENTS:
                if details.startswith(recipient):
                    should_ignore = True
                    break
                    
            if should_ignore:
                continue  # Überspringe diese Zahlung
                
            # Betrag, Währung und Kontostand
            amount_text = cells[3].text.strip()
            # Entferne Tausendertrennzeichen und ersetze Komma durch Punkt
            amount = re.sub(r"['\s]", "", amount_text).replace(",", ".")
            
            currency = cells[4].text.strip() if len(cells) > 4 else "CHF"
            balance = cells[5].text.strip() if len(cells) > 5 else ""

            # Datum validieren, um ungültige Einträge auszufiltern
            if pd.notna(date):
                data.append([date, type, details, amount, currency, balance])
            
        except Exception as e:
            # Fehler bei einer Zeile loggen und weitermachen
            print(f"Fehler beim Verarbeiten einer Zeile: {e}")
            continue

    # DataFrame zurückgeben (auch wenn leer)
    return pd.DataFrame(data, columns=['Date', 'Type', 'Details', 'Amount', 'Currency', 'Balance'])