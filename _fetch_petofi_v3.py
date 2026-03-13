#!/usr/bin/env python3
"""Fetch all 20 Petőfi poems from Hungarian Wikisource API - final version."""
import json
import re
import subprocess
import sys
import time
import urllib.parse

BASE_API = "https://hu.wikisource.org/w/api.php"


def fetch_wikitext(title: str) -> str:
    """Fetch raw wikitext for a page."""
    params = urllib.parse.urlencode({
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "format": "json",
    })
    url = f"{BASE_API}?{params}"
    result = subprocess.run(["curl", "-s", url], capture_output=True, text=True, timeout=30)
    if not result.stdout:
        return ""
    try:
        data = json.loads(result.stdout)
        pages = data["query"]["pages"]
        for pid, page in pages.items():
            if pid == "-1":
                return ""
            return page["revisions"][0]["slots"]["main"]["*"]
    except (json.JSONDecodeError, KeyError, IndexError):
        return ""
    return ""


def extract_poem(wikitext: str) -> str:
    """Extract poem text from wikitext, handling both <poem> tags and : indentation."""
    if not wikitext:
        return ""

    # Remove header template
    text = re.sub(r'\{\{fej\b.*?\}\}', '', wikitext, flags=re.DOTALL)

    # Check for <poem> tags
    poem_matches = re.findall(r'<poem>(.*?)</poem>', text, re.DOTALL)
    if poem_matches:
        # Use only the first poem block (Hungarian text)
        text = poem_matches[0]
    else:
        # Handle two-column tables
        table_match = re.search(r'\{\|.*?\n(.*?)\n\|\}', text, re.DOTALL)
        if table_match:
            table_content = table_match.group(1)
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

    # Remove remaining templates
    text = re.sub(r'\{\{[^}]*\}\}', '', text)
    # Remove categories and interwiki
    text = re.sub(r'\[\[Kategória:[^\]]*\]\]', '', text)
    text = re.sub(r'\[\[[a-z]{2}:[^\]]*\]\]', '', text)
    # Remove table markers
    text = re.sub(r'\{\|.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\|\}', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\|\s*$', '', text, flags=re.MULTILINE)

    # Clean lines
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        line = line.strip()
        if line.startswith(':'):
            line = line[1:]
        # Remove wiki markup
        line = re.sub(r"'''(.*?)'''", r'\1', line)
        line = re.sub(r"''(.*?)''", r'\1', line)
        line = re.sub(r'\[\[[^\|]*\|([^\]]*)\]\]', r'\1', line)
        line = re.sub(r'\[\[([^\]]*)\]\]', r'\1', line)
        line = line.replace('<br>', '').replace('<br />', '').replace('<br/>', '')

        if line.startswith('{|') or line.startswith('|}') or line.startswith('| width'):
            continue
        if line.startswith('|-'):
            continue

        cleaned.append(line)

    text = '\n'.join(cleaned)
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
    ("Itt van az ősz, itt van újra", ["Itt van az ősz, itt van újra…", "Itt van az ősz, itt van újra...", "Itt van az ősz, itt van újra"]),
    ("Ha férfi vagy, légy férfi", ["Ha férfi vagy, légy férfi...", "Ha férfi vagy, légy férfi…"]),
    ("Dalaim", ["Dalaim"]),
    ("A bánat? Egy nagy óceán", ["A bánat? Egy nagy óceán", "A bánat? egy nagy óceán"]),
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
            time.sleep(0.3)

        if not found:
            results[display_title] = "NOT FOUND"
            print(f"  NOT FOUND", file=sys.stderr)

        time.sleep(0.5)

    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Petőfi Sándor - Poemes originals en hongarès\n\n")
        f.write("Font: hu.wikisource.org (domini públic)\n\n")

        found_count = sum(1 for v in results.values() if v != "NOT FOUND")
        not_found_list = [k for k, v in results.items() if v == "NOT FOUND"]
        f.write(f"Poemes trobats: {found_count}/{len(POEMS)}\n\n")
        if not_found_list:
            f.write(f"No trobats: {', '.join(not_found_list)}\n\n")
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
