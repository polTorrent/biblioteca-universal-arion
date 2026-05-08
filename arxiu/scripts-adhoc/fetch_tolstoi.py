#!/usr/bin/env python3
"""Fetch Tolstoy short stories from Russian Wikisource."""
import urllib.request
import urllib.parse
import re
import os

BASE_URL = "https://ru.wikisource.org/w/index.php?title={}&action=raw"

STORIES = {
    "Много_ли_человеку_земли_нужно_(Толстой)": "Много ли человеку земли нужно?",
    "Три_смерти_(Толстой)": "Три смерти",
    "Два_старика_(Толстой)": "Два старика",
    "Чем_люди_живы_(Толстой)": "Чем люди живы",
    "Свечка_(Толстой)": "Свечка",
}

OUTPUT_DIR = "obres/narrativa/lev-tolstoi/quanta-terra-necessita-un-home-i-altres-contes"


def clean_wikitext(text: str) -> str:
    depth = 0
    result = []
    i = 0
    while i < len(text):
        if text[i:i+2] == "{{":
            depth += 1
            i += 2
        elif text[i:i+2] == "}}":
            depth = max(0, depth - 1)
            i += 2
        elif depth == 0:
            result.append(text[i])
            i += 1
        else:
            i += 1
    text = "".join(result)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"__[A-Z]+__", "", text)
    text = re.sub(r"\[\[(?:Категория|Category):[^\]]+\]\]", "", text)
    text = re.sub(r"\[\[[^\]]*\|([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\[http[^\]]*\]", "", text)
    text = re.sub(r"={3,}\s*(.+?)\s*={3,}", r"## \1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main():
    all_texts = []
    for wiki_title, display_title in STORIES.items():
        encoded = urllib.parse.quote(wiki_title)
        url = BASE_URL.format(encoded)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
            cleaned = clean_wikitext(raw)
            if len(cleaned) > 100:
                all_texts.append((display_title, cleaned))
                print(f"OK {display_title}: {len(cleaned)} chars")
            else:
                print(f"FAIL {display_title}: too short ({len(cleaned)} chars)")
        except Exception as e:
            print(f"FAIL {display_title}: {e}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, "original.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Рассказы Льва Толстого\n")
        f.write("# Contes de Lev Tolstoi - Textos originals en rus\n\n")
        f.write("Font: Wikisource (ru.wikisource.org) - Domini public\n\n---\n\n")
        for title, text in all_texts:
            f.write(f"# {title}\n\n")
            f.write(text)
            f.write("\n\n---\n\n")
    print(f"\nEscrit original.md amb {len(all_texts)} contes")


if __name__ == "__main__":
    main()
