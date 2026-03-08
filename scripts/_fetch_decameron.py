#!/usr/bin/env python3
"""Fetch 10 selected novellas from Boccaccio's Decameron from Italian Wikisource."""

import json
import urllib.request
import urllib.parse
import re
import sys
import time
from pathlib import Path

BASE = "https://it.wikisource.org/w/api.php"
HEADERS = {"User-Agent": "BibliotecaArion/1.0"}

# 10 most famous/representative novellas (correct Wikisource page titles)
NOVELLAS = [
    ("Decameron/Giornata prima/Novella prima", "Giornata I, Novella 1 - Ser Ciappelletto"),
    ("Decameron/Giornata prima/Novella terza", "Giornata I, Novella 3 - L'anell dels tres anells (Melchisedech)"),
    ("Decameron/Giornata seconda/Novella settima", "Giornata II, Novella 7 - El soldà de Babilònia"),
    ("Decameron/Giornata terza/Novella prima", "Giornata III, Novella 1 - Masetto da Lamporecchio"),
    ("Decameron/Giornata quarta/Novella prima", "Giornata IV, Novella 1 - Tancredi i Ghismonda"),
    ("Decameron/Giornata quarta/Novella quinta", "Giornata IV, Novella 5 - El test de Lisabetta"),
    ("Decameron/Giornata quinta/Novella nona", "Giornata V, Novella 9 - Federigo degli Alberighi"),
    ("Decameron/Giornata sesta/Novella nona", "Giornata VI, Novella 9 - Guido Cavalcanti"),
    ("Decameron/Giornata ottava/Novella terza", "Giornata VIII, Novella 3 - Calandrino i l'heliotropi"),
    ("Decameron/Giornata decima/Novella decima", "Giornata X, Novella 10 - Griselda"),
]

def fetch_page(title):
    """Fetch wikitext of a page from Italian Wikisource."""
    params = urllib.parse.urlencode({
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "format": "json",
    })
    url = f"{BASE}?{params}"
    req = urllib.request.Request(url, headers=HEADERS)
    resp = urllib.request.urlopen(req, timeout=30)
    data = json.loads(resp.read())
    pages = data.get("query", {}).get("pages", {})
    for pid, page in pages.items():
        if pid == "-1":
            return None
        revs = page.get("revisions", [])
        if revs:
            return revs[0].get("slots", {}).get("main", {}).get("*", "")
    return None


def clean_wikitext(text):
    """Basic cleanup of wikitext to plain text."""
    if not text:
        return ""
    # Remove common templates
    text = re.sub(r"\{\{[^}]*\}\}", "", text)
    # Remove categories
    text = re.sub(r"\[\[Categoria:[^\]]*\]\]", "", text)
    # Convert wiki links [[text|display]] -> display, [[text]] -> text
    text = re.sub(r"\[\[[^|\]]*\|([^\]]*)\]\]", r"\1", text)
    text = re.sub(r"\[\[([^\]]*)\]\]", r"\1", text)
    # Remove bold/italic wiki markup
    text = re.sub(r"'{2,5}", "", text)
    # Remove <ref> tags
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.DOTALL)
    text = re.sub(r"<ref[^/]*/>", "", text)
    # Remove other HTML tags but keep content
    text = re.sub(r"<[^>]+>", "", text)
    # Remove section headers (== text ==)
    text = re.sub(r"^=+\s*.*?\s*=+$", "", text, flags=re.MULTILINE)
    # Clean up whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main():
    output_dir = Path("/home/jo/biblioteca-universal-arion/obres/narrativa/boccaccio/decamero-seleccio-10-contes")
    output_dir.mkdir(parents=True, exist_ok=True)

    all_text = []
    all_text.append("# Decameron — Selecció de 10 contes\n")
    all_text.append("## Giovanni Boccaccio\n")
    all_text.append("*Text original en italià (segle XIV)*\n")
    all_text.append("*Font: Wikisource italiana*\n\n---\n")

    success_count = 0
    for i, (page_title, desc) in enumerate(NOVELLAS, 1):
        print(f"[{i}/10] Baixant: {page_title} ...")
        wikitext = fetch_page(page_title)
        if wikitext:
            cleaned = clean_wikitext(wikitext)
            if len(cleaned) > 100:
                all_text.append(f"\n## {desc}\n")
                all_text.append(f"*({page_title})*\n\n")
                all_text.append(cleaned)
                all_text.append("\n\n---\n")
                success_count += 1
                print(f"  OK ({len(cleaned)} chars)")
            else:
                print(f"  WARN: text massa curt ({len(cleaned)} chars)")
                # Try alternative page names
        else:
            print(f"  WARN: pàgina no trobada")
        time.sleep(1)  # Be polite

    if success_count == 0:
        # Try alternative page structure
        print("\nProvant estructura alternativa...")
        alt_novellas = [
            ("Decameron/Giornata_prima/Novella_prima", "Giornata I, Novella 1"),
            ("Decameron/Prima_giornata/Novella_prima", "Giornata I, Novella 1"),
        ]
        for page_title, desc in alt_novellas:
            print(f"  Provant: {page_title}")
            wikitext = fetch_page(page_title)
            if wikitext:
                print(f"  TROBAT! ({len(wikitext)} chars)")
                break
            time.sleep(1)

    if success_count > 0:
        original_path = output_dir / "original.md"
        original_path.write_text("\n".join(all_text), encoding="utf-8")
        print(f"\nEscrit {original_path} ({success_count}/10 contes, {len(''.join(all_text))} chars)")
    else:
        print("\nERROR: No s'ha pogut obtenir cap conte")
        sys.exit(1)


if __name__ == "__main__":
    main()
