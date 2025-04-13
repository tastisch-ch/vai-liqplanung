import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime

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
    soup = BeautifulSoup(html_string, 'html.parser')
    rows = soup.find_all('tr')
    data = []
    for row in rows:
        cells = row.find_all('td')
        if not cells:
            continue

        date_str = cells[0].find('span', class_='print').text.strip()
        date = parse_date_swiss_fallback(date_str)
        type = cells[1].text.strip()
        if type == "Dauerauftrag":
            continue  # Ignoriere Daueraufträge
        details = cells[2].find('span', class_='text').text.strip()
        amount = cells[3].text.strip().replace("'", "")
        currency = cells[4].text.strip()
        balance = cells[5].text.strip()

        data.append([date, type, details, amount, currency, balance])

    return pd.DataFrame(data, columns=['Date', 'Type', 'Details', 'Amount', 'Currency', 'Balance'])
