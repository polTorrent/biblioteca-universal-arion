#!/usr/bin/env python3
"""Fetch all 20 Petőfi poems from Hungarian Wikisource - final version."""
import json
import re
import sys
import time
import urllib.parse
import urllib.request

BASE_API = "https://hu.wikisource.org/w/api.php"


def fetch_wikitext(title: str) -> str:
    """Fetch raw wikitext using urllib to handle special chars properly."""
    params = urllib.parse.urlencode({
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "format": "json",
    })
    url = f"{BASE_API}?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BibliotecaArion/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            pages = data["query"]["pages"]
            for pid, page in pages.items():
                if pid == "-1":
                    return ""
                return page["revisions"][0]["slots"]["main"]["*"]
    except Exception as e:
        print(f"  Error: {e}", file=sys.stderr)
        return ""
    return ""


def extract_poem(wikitext: str) -> str:
    """Extract clean Hungarian poem text from wikitext."""
    if not wikitext:
        return ""

    # Remove header template
    text = re.sub(r'\{\{fej\b.*?\}\}', '', wikitext, flags=re.DOTALL)
    # Remove any remaining templates
    text = re.sub(r'\{\{[^}]*\}\}', '', text)

    # Extract from <poem> tags if present
    poem_matches = re.findall(r'<poem>(.*?)</poem>', text, re.DOTALL)
    if poem_matches:
        text = poem_matches[0]
    else:
        # Handle two-column tables (Hungarian | other language)
        table_match = re.search(r'\{\|.*?\n(.*?)\n\|\}', text, re.DOTALL)
        if table_match:
            table_content = table_match.group(1)
            # Split by column separator
            parts = re.split(r'\n\|\s*\n', table_content)
            if len(parts) >= 2:
                text = parts[0]
            else:
                parts = re.split(r'\n\|\s*$', table_content, flags=re.MULTILINE)
                if len(parts) >= 2:
                    text = parts[0]
                else:
                    text = table_content
            text = re.sub(r'^\|\s*width=.*?\|\s*$', '', text, flags=re.MULTILINE)

    # Remove remaining markup
    text = re.sub(r'\[\[Kategória:[^\]]*\]\]', '', text)
    text = re.sub(r'\[\[[a-z]{2}:[^\]]*\]\]', '', text)
    text = re.sub(r'\{\|.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\|\}', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\|\s*$', '', text, flags=re.MULTILINE)
    # Remove <poem> tags if any remain
    text = text.replace('<poem>', '').replace('</poem>', '')

    # Clean individual lines
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        line = line.strip()
        # Remove : prefix (wiki indentation for poetry)
        if line.startswith(':'):
            line = line[1:]
        # Remove wiki formatting
        line = re.sub(r"'''(.*?)'''", r'\1', line)
        line = re.sub(r"''(.*?)''", r'\1', line)
        line = re.sub(r'\[\[[^\|]*\|([^\]]*)\]\]', r'\1', line)
        line = re.sub(r'\[\[([^\]]*)\]\]', r'\1', line)
        line = line.replace('<br>', '').replace('<br />', '').replace('<br/>', '')
        # Skip table formatting lines
        if line.startswith('{|') or line.startswith('|}') or line.startswith('| width') or line.startswith('|-'):
            continue
        cleaned.append(line)

    text = '\n'.join(cleaned)
    # Collapse multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return text


# (display_title, [wikisource_titles_to_try])
POEMS = [
    ("Nemzeti dal", ["Nemzeti dal"]),
    ("Szeptember végén", ["Szeptember végén"]),
    ("Egy gondolat bánt engemet", ["Egy gondolat bánt engemet...", "Egy gondolat bánt engemet…"]),
    ("A Tisza", ["A Tisza"]),
    ("Föltámadott a tenger", ["Föltámadott a tenger...", "Föltámadott a tenger…"]),
    ("Reszket a bokor, mert...", ["Reszket a bokor, mert...", "Reszket a bokor, mert…"]),
    ("Az Alföld", ["Az Alföld", "Az alföld"]),
    ("Befordúltam a konyhára", ["Befordúltam a konyhára...", "Befordúltam a konyhára…"]),
    ("A XIX. század költői", ["A XIX. század költői"]),
    ("Fa leszek, ha...", ["Fa leszek, ha...", "Fa leszek, ha…"]),
    ("Minek nevezzelek?", ["Minek nevezzelek?"]),
    ("Anyám tyúkja", ["Anyám tyúkja"]),
    ("A puszta, télen", ["A puszta, télen"]),
    ("Itt van az ősz, itt van újra", ["Itt van az ősz, itt van újra…", "Itt van az ősz, itt van újra..."]),
    ("Ha férfi vagy, légy férfi", ["Ha férfi vagy, légy férfi...", "Ha férfi vagy, légy férfi…"]),
    ("Dalaim", ["Dalaim"]),
    ("A bánat? Egy nagy óceán", ["A bánat? Egy nagy óceán"]),
    ("Szabadság, szerelem!", ["Szabadság, szerelem!"]),
    ("Honfidal", ["Honfidal"]),
    ("Istentelen egy élet", ["Istentelen egy élet...", "Istentelen egy élet…", "Istentelen egy élet"]),
]


def main():
    output_file = "/home/jo/biblioteca-universal-arion/_petofi_poems.md"
    results = {}

    for display_title, wiki_titles in POEMS:
        print(f"\n--- {display_title} ---", file=sys.stderr)

        found = False
        for wiki_title in wiki_titles:
            wikitext = fetch_wikitext(wiki_title)
            if wikitext and len(wikitext) > 50:
                poem = extract_poem(wikitext)
                if poem and len(poem) > 20:
                    results[display_title] = poem
                    print(f"  OK via '{wiki_title}' ({len(poem)} chars)", file=sys.stderr)
                    found = True
                    break
                else:
                    print(f"  Page found but extraction failed ({len(poem) if poem else 0} chars)", file=sys.stderr)
            time.sleep(0.3)

        if not found:
            results[display_title] = "NOT FOUND"
            print(f"  NOT FOUND on Wikisource", file=sys.stderr)

        time.sleep(0.5)

    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Petőfi Sándor - Poemes originals en hongarès\n\n")
        f.write("Font: hu.wikisource.org (domini públic)\n\n")

        found_count = sum(1 for v in results.values() if v != "NOT FOUND")
        not_found_list = [k for k, v in results.items() if v == "NOT FOUND"]
        f.write(f"Poemes trobats: {found_count}/{len(POEMS)}\n\n")
        if not_found_list:
            f.write(f"No trobats a Wikisource: {', '.join(not_found_list)}\n\n")
        f.write("---\n\n")

        for title, text in results.items():
            f.write(f"## {title}\n\n")
            f.write(text)
            f.write("\n\n---\n\n")

    print(f"\nResults written to {output_file}", file=sys.stderr)
    print(f"Found {found_count}/{len(POEMS)} poems", file=sys.stderr)
    for nf in not_found_list:
        print(f"  NOT FOUND: {nf}", file=sys.stderr)


if __name__ == "__main__":
    main()
