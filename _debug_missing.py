#!/usr/bin/env python3
"""Debug missing poems - check what the API returns."""
import subprocess
import json
import urllib.parse
import time

API = "https://hu.wikisource.org/w/api.php"


def fetch_raw(title):
    params = urllib.parse.urlencode({
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "format": "json",
    })
    url = f"{API}?{params}"
    result = subprocess.run(["curl", "-s", url], capture_output=True, text=True, timeout=30)
    data = json.loads(result.stdout)
    pages = data["query"]["pages"]
    for pid, page in pages.items():
        if pid == "-1":
            return f"PAGE NOT FOUND (title: {title})"
        wt = page["revisions"][0]["slots"]["main"]["*"]
        return wt[:500]
    return "EMPTY"


titles_to_check = [
    "Minek nevezzelek?",
    "Minek nevezzelek",
    "Minek nevezzelek?...",
    "A puszta, télen",
    "A puszta télen",
    "A puszta, télen (Petőfi Sándor)",
    "Ha férfi vagy, légy férfi...",
    "Ha férfi vagy, légy férfi",
    "A bánat? Egy nagy óceán",
    "A bánat? egy nagy óceán",
    "A bánat? Egy nagy óceán...",
    "Honfidal",
    "Honfidal (Petőfi)",
    "Istentelen egy élet...",
    "Istentelen egy élet…",
    "Istentelen egy élet",
]

for t in titles_to_check:
    result = fetch_raw(t)
    status = "FOUND" if "PAGE NOT FOUND" not in result else "MISSING"
    print(f"[{status}] {t}")
    if status == "FOUND":
        print(f"  Preview: {result[:200]}")
    time.sleep(0.3)
