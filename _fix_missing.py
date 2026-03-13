#!/usr/bin/env python3
"""Fix missing poems by properly URL-encoding titles with special chars."""
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

BASE_API = "https://hu.wikisource.org/w/api.php"


def fetch_wikitext(title: str) -> str:
    """Fetch raw wikitext using urllib instead of curl to handle ? properly."""
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
        print(f"  Error fetching '{title}': {e}", file=sys.stderr)
        return ""
    return ""


def extract_poem(wikitext: str) -> str:
    """Extract poem text from wikitext."""
    if not wikitext:
        return ""

    text = re.sub(r'\{\{fej\b.*?\}\}', '', wikitext, flags=re.DOTALL)

    poem_matches = re.findall(r'<poem>(.*?)</poem>', text, re.DOTALL)
    if poem_matches:
        text = poem_matches[0]
    else:
        table_match = re.search(r'\{\|.*?\n(.*?)\n\|\}', text, re.DOTALL)
        if table_match:
            table_content = table_match.group(1)
            parts = re.split(r'\n\|\s*\n', table_content)
            if len(parts) >= 2:
                text = parts[0]
            text = re.sub(r'^\|\s*width=.*?\|\s*$', '', text, flags=re.MULTILINE)

    text = re.sub(r'\{\{[^}]*\}\}', '', text)
    text = re.sub(r'\[\[Kategória:[^\]]*\]\]', '', text)
    text = re.sub(r'\[\[[a-z]{2}:[^\]]*\]\]', '', text)
    text = re.sub(r'\{\|.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\|\}', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\|\s*$', '', text, flags=re.MULTILINE)

    lines = text.split('\n')
    cleaned = []
    for line in lines:
        line = line.strip()
        if line.startswith(':'):
            line = line[1:]
        line = re.sub(r"'''(.*?)'''", r'\1', line)
        line = re.sub(r"''(.*?)''", r'\1', line)
        line = re.sub(r'\[\[[^\|]*\|([^\]]*)\]\]', r'\1', line)
        line = re.sub(r'\[\[([^\]]*)\]\]', r'\1', line)
        line = line.replace('<br>', '').replace('<br />', '').replace('<br/>', '')
        if line.startswith('{|') or line.startswith('|}') or line.startswith('| width') or line.startswith('|-'):
            continue
        cleaned.append(line)

    text = '\n'.join(cleaned)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


MISSING = [
    ("Minek nevezzelek?", ["Minek nevezzelek?"]),
    ("A puszta, télen", ["A puszta, télen"]),
    ("Ha férfi vagy, légy férfi", ["Ha férfi vagy, légy férfi..."]),
    ("A bánat? Egy nagy óceán", ["A bánat? Egy nagy óceán"]),
    ("Honfidal", ["Honfidal"]),
    ("Istentelen egy élet", ["Istentelen egy élet...", "Istentelen egy élet…", "Istentelen egy élet"]),
]

for display, titles in MISSING:
    print(f"\n--- {display} ---", file=sys.stderr)
    for t in titles:
        wikitext = fetch_wikitext(t)
        if wikitext:
            print(f"  FOUND via '{t}' ({len(wikitext)} chars wikitext)", file=sys.stderr)
            poem = extract_poem(wikitext)
            print(f"  Extracted: {len(poem)} chars", file=sys.stderr)
            if poem:
                print(f"  First 200: {poem[:200]}", file=sys.stderr)
            break
        time.sleep(0.3)
    else:
        print(f"  NOT FOUND at all", file=sys.stderr)
