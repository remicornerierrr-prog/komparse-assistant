import requests
from bs4 import BeautifulSoup
from html import unescape

URL = "https://komparse.de/hauptframe.htm"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# ------------------------------------------------------------
# 1. Télécharger la page Komparse
# ------------------------------------------------------------

response = requests.get(URL, headers=headers, timeout=20)
response.raise_for_status()

print("Statut HTTP :", response.status_code)
print("Encodage détecté par requests :", response.encoding)
print("Encodage apparent :", response.apparent_encoding)

# ------------------------------------------------------------
# 2. Décoder correctement le contenu
# ------------------------------------------------------------
#
# Komparse utilise un ancien encodage de page.
# On décode donc les octets bruts en Windows-1252.
#

html_source = response.content.decode("cp1252", errors="replace")

print("Taille HTML :", len(html_source), "caractères")

# ------------------------------------------------------------
# 3. Analyser le HTML avec BeautifulSoup
# ------------------------------------------------------------

soup = BeautifulSoup(html_source, "html.parser")

# ------------------------------------------------------------
# 4. Récupérer le texte de la page
# ------------------------------------------------------------

text = soup.get_text("\n", strip=True)

# Convertir les entités HTML éventuelles :
# &#xA0; -> espace
# &#xA;  -> retour à la ligne
text = unescape(text)

# ------------------------------------------------------------
# 5. Afficher un extrait dans le terminal
# ------------------------------------------------------------

print("\n--- EXTRAIT DE LA PAGE ---\n")
print(text[:5000])

# ------------------------------------------------------------
# 6. Créer notre propre fichier HTML UTF-8
# ------------------------------------------------------------

html_output = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Komparse</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 40px auto;
            padding: 0 20px;
            line-height: 1.5;
        }}

        pre {{
            white-space: pre-wrap;
            font-family: Arial, sans-serif;
        }}
    </style>
</head>

<body>

<h1>Test du scraper Komparse</h1>

<pre>{text}</pre>

</body>
</html>
"""

# ------------------------------------------------------------
# 7. Enregistrer le fichier en UTF-8
# ------------------------------------------------------------

output_file = "komparse_test.html"

with open(output_file, "w", encoding="utf-8") as f:
    f.write(html_output)

print("\n----------------------------------------")
print("Fichier créé :", output_file)
print("----------------------------------------")