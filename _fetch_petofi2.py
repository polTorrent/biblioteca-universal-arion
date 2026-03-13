#!/usr/bin/env python3
"""Fetch Petőfi poems from Hungarian Wikisource API and extract Hungarian text."""
import json
import re
import subprocess
import sys
import time
import urllib.parse

BASE_API = "https://hu.wikisource.org/w/api.php"


def search_poem(query: str) -> list[str]:
    """Search Wikisource for a poem title."""
    params = urllib.parse.urlencode({
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json",
        "srlimit": 5,
    })
    url = f"{BASE_API}?{params}"
    result = subprocess.run(["curl", "-s", url], capture_output=True, text=True, timeout=30)
    try:
        data = json.loads(result.stdout)
        return [r["title"] for r in data["query"]["search"]]
    except (json.JSONDecodeError, KeyError):
        return []


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


def extract_hungarian_poem(wikitext: str) -> str:
    """Extract the Hungarian poem text from wikitext, removing templates and other languages."""
    if not wikitext:
        return ""

    # Remove header template
    text = re.sub(r'\{\{fej\b.*?\}\}', '', wikitext, flags=re.DOTALL)
    # Remove other templates
    text = re.sub(r'\{\{[^}]*\}\}', '', text)
    # Remove categories
    text = re.sub(r'\[\[Kategória:[^\]]*\]\]', '', text)
    # Remove interwiki links
    text = re.sub(r'\[\[[a-z]{2}:[^\]]*\]\]', '', text)

    # Handle two-column tables (Hungarian | other language)
    # Extract only the first column (Hungarian)
    table_match = re.search(r'\{\|.*?\n(.*?)\n\|\}', text, re.DOTALL)
    if table_match:
        table_content = table_match.group(1)
        # Split by column separator
        columns = re.split(r'\n\|(?!\|)\s*\n', table_content)
        if not columns:
            columns = re.split(r'\n\|\s*$', table_content, flags=re.MULTILINE)
        if columns:
            text = columns[0]
            # Remove table markup
            text = re.sub(r'^\|\s*width=.*?\|\s*$', '', text, flags=re.MULTILINE)
            text = re.sub(r'^\|\s*$', '', text, flags=re.MULTILINE)
    else:
        # Remove table markers if they exist
        text = re.sub(r'\{\|.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\|\}', '', text, flags=re.MULTILINE)

    # Clean poem lines (remove : prefix used for indentation)
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        line = line.strip()
        if line.startswith(':'):
            line = line[1:]
        # Remove wiki markup
        line = re.sub(r"'''(.*?)'''", r'\1', line)  # bold
        line = re.sub(r"''(.*?)''", r'\1', line)    # italic
        line = re.sub(r'\[\[[^\|]*\|([^\]]*)\]\]', r'\1', line)  # [[link|text]]
        line = re.sub(r'\[\[([^\]]*)\]\]', r'\1', line)  # [[link]]
        line = line.replace('<br>', '').replace('<br />', '').replace('<br/>', '')

        # Skip table formatting lines
        if line.startswith('{|') or line.startswith('|}') or line.startswith('| width'):
            continue
        if line.startswith('|-'):
            continue

        cleaned.append(line)

    text = '\n'.join(cleaned)

    # Clean up whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return text


# Poems to find: (search query, expected title or None to search)
POEMS = [
    ("Nemzeti dal", "Nemzeti dal"),
    ("Szeptember végén", "Szeptember végén"),
    ("Egy gondolat bánt engemet", "Egy gondolat bánt engemet..."),
    ("A Tisza Petőfi", "A Tisza"),
    ("Föltámadott a tenger", "Föltámadott a tenger..."),
    ("Reszket a bokor mert", "Reszket a bokor, mert..."),
    ("Az alföld Petőfi", "Az alföld"),
    ("Befordúltam a konyhára", "Befordúltam a konyhára..."),
    ("A XIX. század költői", "A XIX. század költői"),
    ("Fa leszek ha Petőfi", "Fa leszek, ha..."),
    ("Minek nevezzelek Petőfi", "Minek nevezzelek?"),
    ("Anyám tyúkja Petőfi", "Anyám tyúkja"),
    ("A puszta télen Petőfi", "A puszta, télen"),
    ("Itt van az ősz itt van újra", "Itt van az ősz, itt van újra"),
    ("Ha férfi vagy légy férfi", "Ha férfi vagy, légy férfi"),
    ("Dalaim Petőfi", "Dalaim"),
    ("A bánat egy nagy óceán", "A bánat? egy nagy óceán"),
    ("Szabadság szerelem Petőfi", "Szabadság, szerelem!"),
    ("Honfidal Petőfi", "Honfidal"),
    ("Istentelen egy élet", None),
]


def main():
    output_file = "/home/jo/biblioteca-universal-arion/_petofi_poems.md"
    results = {}

    for search_q, expected_title in POEMS:
        display = expected_title or search_q
        print(f"\n--- {display} ---", file=sys.stderr)

        # First try the expected title directly
        if expected_title:
            wikitext = fetch_wikitext(expected_title)
            if wikitext and len(wikitext) > 50:
                poem = extract_hungarian_poem(wikitext)
                if poem and len(poem) > 20:
                    results[display] = poem
                    print(f"  OK (direct: {len(poem)} chars)", file=sys.stderr)
                    time.sleep(0.5)
                    continue

        # Try variations with ellipsis
        if expected_title:
            for variant in [
                expected_title + "...",
                expected_title + "…",
                expected_title.rstrip("...").rstrip("…"),
                expected_title.rstrip("...").rstrip("…") + "…",
            ]:
                if variant == expected_title:
                    continue
                wikitext = fetch_wikitext(variant)
                if wikitext and len(wikitext) > 50:
                    poem = extract_hungarian_poem(wikitext)
                    if poem and len(poem) > 20:
                        results[display] = poem
                        print(f"  OK (variant '{variant}': {len(poem)} chars)", file=sys.stderr)
                        break
                time.sleep(0.3)
            else:
                # Search
                print(f"  Searching for: {search_q}", file=sys.stderr)
                titles = search_poem(f"Petőfi {search_q}")
                print(f"  Search results: {titles}", file=sys.stderr)
                found = False
                for title in titles[:3]:
                    wikitext = fetch_wikitext(title)
                    if wikitext and len(wikitext) > 50:
                        poem = extract_hungarian_poem(wikitext)
                        if poem and len(poem) > 20:
                            results[display] = poem
                            print(f"  OK (search hit '{title}': {len(poem)} chars)", file=sys.stderr)
                            found = True
                            break
                    time.sleep(0.3)
                if not found:
                    results[display] = "NOT FOUND"
                    print(f"  NOT FOUND", file=sys.stderr)
        else:
            # No expected title, just search
            print(f"  Searching for: {search_q}", file=sys.stderr)
            titles = search_poem(f"Petőfi {search_q}")
            print(f"  Search results: {titles}", file=sys.stderr)
            found = False
            for title in titles[:3]:
                wikitext = fetch_wikitext(title)
                if wikitext and len(wikitext) > 50:
                    poem = extract_hungarian_poem(wikitext)
                    if poem and len(poem) > 20:
                        results[title] = poem
                        print(f"  OK (search hit '{title}': {len(poem)} chars)", file=sys.stderr)
                        found = True
                        break
                time.sleep(0.3)
            if not found:
                results[search_q] = "NOT FOUND"
                print(f"  NOT FOUND", file=sys.stderr)

        time.sleep(0.5)

    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Petőfi Sándor - Poemes originals en hongarès\n\n")
        f.write("Font: hu.wikisource.org (domini públic)\n\n")

        found = sum(1 for v in results.values() if v != "NOT FOUND" and not v.startswith("ERROR"))
        not_found = [k for k, v in results.items() if v == "NOT FOUND" or v.startswith("ERROR")]
        f.write(f"Poemes trobats: {found}/{len(POEMS)}\n\n")
        if not_found:
            f.write(f"No trobats: {', '.join(not_found)}\n\n")
        f.write("---\n\n")

        for title, text in results.items():
            f.write(f"## {title}\n\n")
            f.write(text)
            f.write("\n\n---\n\n")

    print(f"\nResults written to {output_file}", file=sys.stderr)
    print(f"Found {found}/{len(POEMS)} poems", file=sys.stderr)
    for nf in not_found:
        print(f"  NOT FOUND: {nf}", file=sys.stderr)


if __name__ == "__main__":
    main()
