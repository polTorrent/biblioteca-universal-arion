#!/usr/bin/env python3
"""Descarrega els Analectes (Lúnyǔ) Llibres I-IV des de Wikisource xinès."""
import json
import re
import urllib.request
import urllib.parse
import sys

BOOKS = {
    "學而第一": "Llibre I · Xué ér (Aprendre)",
    "為政第二": "Llibre II · Wéi zhèng (Governar)",
    "八佾第三": "Llibre III · Bā yì (Vuit fileres de dansaires)",
    "里仁第四": "Llibre IV · Lǐ rén (La benevolència en la comunitat)",
}

def fetch_book(book_name: str) -> str:
    """Fetch a book from Chinese Wikisource."""
    title = f"論語/{book_name}"
    url = (
        "https://zh.wikisource.org/w/api.php?"
        + urllib.parse.urlencode({
            "action": "query",
            "titles": title,
            "prop": "revisions",
            "rvprop": "content",
            "format": "json",
            "rvslots": "main",
        })
    )
    req = urllib.request.Request(url, headers={"User-Agent": "BibliotecaArion/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    pages = data["query"]["pages"]
    for pid, page in pages.items():
        if pid == "-1":
            return ""
        content = page["revisions"][0]["slots"]["main"]["*"]
        # Remove wiki markup
        content = re.sub(r'\{\{[^}]*\}\}', '', content)
        content = re.sub(r'\[\[([^\]|]*\|)?([^\]]*)\]\]', r'\2', content)
        content = re.sub(r"'{2,}", '', content)
        content = re.sub(r'<[^>]+/?>', '', content)
        content = re.sub(r'==+\s*[^=]+\s*=+', '', content)
        lines = [l.strip() for l in content.split('\n') if l.strip()]
        return '\n\n'.join(lines)
    return ""


def main():
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "."

    parts = []
    parts.append("# 論語 · Lúnyǔ — Analectes")
    parts.append("")
    parts.append("**Confuci (孔子, Kǒngzǐ, c. 551–479 aC)**")
    parts.append("")
    parts.append("Selecció: Llibres I–IV")
    parts.append("")
    parts.append("Font: [Wikisource xinès](https://zh.wikisource.org/wiki/論語)")
    parts.append("")
    parts.append("---")
    parts.append("")

    for book_name, cat_title in BOOKS.items():
        print(f"Descarregant {book_name}...", file=sys.stderr)
        text = fetch_book(book_name)
        if not text:
            print(f"ERROR: No s'ha pogut descarregar {book_name}", file=sys.stderr)
            sys.exit(1)
        parts.append(f"## {cat_title}")
        parts.append(f"### {book_name}")
        parts.append("")
        parts.append(text)
        parts.append("")
        parts.append("---")
        parts.append("")

    output_path = f"{output_dir}/original.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write('\n'.join(parts))

    print(f"✅ Escrit a {output_path}", file=sys.stderr)

    # Count characters
    full_text = '\n'.join(parts)
    chars = len(re.sub(r'\s+', '', re.sub(r'[#\-*\[\]()a-zA-Z·—àèéíòóúïüç:/.]+', '', full_text)))
    print(f"   {chars} caràcters xinesos", file=sys.stderr)


if __name__ == "__main__":
    main()
