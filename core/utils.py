import base64

# ----------------------------------
# 🪐 CHF-Beträge schön formatieren
# ----------------------------------
def chf_format(x):
    try:
        return f"CHF {x:,.2f}".replace(",", "'")
    except:
        return x

# ----------------------------------
# 🖼️ Firmenlogo einbetten
# ----------------------------------
def load_svg_logo(path):
    with open(path, "rb") as f:
        svg = f.read()
    b64_svg = base64.b64encode(svg).decode("utf-8")
    return f"data:image/svg+xml;base64,{b64_svg}"
