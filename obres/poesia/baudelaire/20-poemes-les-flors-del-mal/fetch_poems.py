#!/usr/bin/env python3
"""Fetch 20 poems from Les Fleurs du Mal from Wikisource."""
import subprocess
import json
import html
import re
import time

POEMS = [
    ("Au Lecteur", "Les_Fleurs_du_mal_(1861)/Au_lecteur"),
    ("L'Albatros", "Les_Fleurs_du_mal_(1868)/L%E2%80%99Albatros"),
    ("Correspondances", "Les_Fleurs_du_mal_(1868)/Correspondances"),
    ("L'Ennemi", "Les_Fleurs_du_mal_(1868)/L%E2%80%99Ennemi"),
    ("La Vie antérieure", "Les_Fleurs_du_mal_(1868)/La_Vie_ant%C3%A9rieure"),
    ("L'Homme et la Mer", "Les_Fleurs_du_mal_(1868)/L%E2%80%99Homme_et_la_mer"),
    ("La Beauté", "Les_Fleurs_du_mal_(1868)/La_Beaut%C3%A9"),
    ("Hymne à la Beauté", "Les_Fleurs_du_mal_(1868)/Hymne_%C3%A0_la_beaut%C3%A9"),
    ("Parfum exotique", "Les_Fleurs_du_mal_(1868)/Parfum_exotique"),
    ("La Chevelure", "Les_Fleurs_du_mal_(1868)/La_Chevelure"),
    ("Harmonie du soir", "Les_Fleurs_du_mal_(1868)/Harmonie_du_soir"),
    ("L'Invitation au voyage", "Les_Fleurs_du_mal_(1868)/L%E2%80%99Invitation_au_voyage"),
    ("Spleen (LXXVIII)", "Les_Fleurs_du_mal_(1868)/Spleen_(%C2%AB_Quand_le_ciel_bas_et_lourd_p%C3%A8se_comme_un_couvercle_%C2%BB)"),
    ("Le Vampire", "Les_Fleurs_du_mal_(1868)/Le_Vampire"),
    ("Une Charogne", "Les_Fleurs_du_mal_(1868)/Une_charogne"),
    ("Le Chat", "Les_Fleurs_du_mal_(1868)/Le_Chat_(%C2%AB_Viens,_mon_beau_chat,_sur_mon_c%C5%93ur_amoureux_%C2%BB)"),
    ("Le Balcon", "Les_Fleurs_du_mal_(1868)/Le_Balcon"),
    ("Recueillement", "Les_Fleurs_du_mal_(1868)/Recueillement"),
    ("L'Irrémédiable", "Les_Fleurs_du_mal_(1868)/L%E2%80%99Irrem%C3%A9diable"),
    ("Le Voyage", "Les_Fleurs_du_mal_(1868)/Le_Voyage"),
]

def fetch_poem(page):
    url = f"https://fr.wikisource.org/w/api.php?action=parse&page={page}&prop=text&format=json"
    r = subprocess.run(["curl", "-sL", url], capture_output=True, text=True)
    d = json.loads(r.stdout)
    if "error" in d:
        return None
    t = d.get("parse", {}).get("text", {}).get("*", "")
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t)
    lines = []
    for l in t.split("\n"):
        l = l.strip()
        if not l:
            continue
        if l.startswith(".mw-") or l.startswith("@media") or "headertemplate" in l:
            continue
        if len(l) > 300:
            continue
        if "Fichier" in l and "Portail" in l:
            continue
        if "Pour les autres" in l:
            continue
        if l.startswith("collection"):
            continue
        if "Charles Baudelaire" == l:
            continue
        if "Michel Lévy" in l or "Poulet-Malassis" in l:
            continue
        if l.startswith("1868") or l.startswith("1861"):
            continue
        if l.startswith("Paris"):
            continue
        if "Œuvres complètes" in l:
            continue
        if l.startswith("Baudelaire Les Fleurs") or l.startswith("Baudelaire - Les"):
            continue
        lines.append(l)
    return "\n".join(lines)

output = []
for title, page in POEMS:
    print(f"Fetching: {title}...")
    text = fetch_poem(page)
    if text:
        output.append(f"## {title}\n\n{text}")
    else:
        output.append(f"## {title}\n\n[ERROR: Could not fetch]")
    time.sleep(0.5)

with open("obres/poesia/baudelaire/20-poemes-les-flors-del-mal/raw_poems.txt", "w") as f:
    f.write("\n\n---\n\n".join(output))

print("Done! Saved to raw_poems.txt")
