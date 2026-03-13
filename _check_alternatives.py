#!/usr/bin/env python3
"""Check alternative titles that might be 'Istentelen egy élet'."""
import urllib.request
import urllib.parse
import json

API = "https://hu.wikisource.org/w/api.php"

titles_to_check = [
    "Élet, halál",
    "Élet, halál... nekem már mindegy",
    "Élet vagy halál!",
    "Ez már aztán az élet!",
]

for title in titles_to_check:
    params = urllib.parse.urlencode({
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "format": "json",
    })
    url = f"{API}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "BibliotecaArion/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        pages = data["query"]["pages"]
        for pid, page in pages.items():
            if pid == "-1":
                print(f"NOT FOUND: {title}")
            else:
                content = page["revisions"][0]["slots"]["main"]["*"]
                if "istentelen" in content.lower():
                    print(f"MATCH: {title}")
                    print(content[:500])
                else:
                    print(f"Found but no 'istentelen': {title}")
                    print(content[:200])
                print()
