#!/usr/bin/env python3
"""Check remaining missing poems."""
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
    if not result.stdout:
        return "EMPTY RESPONSE"
    data = json.loads(result.stdout)
    pages = data["query"]["pages"]
    for pid, page in pages.items():
        if pid == "-1":
            return "PAGE NOT FOUND"
        wt = page["revisions"][0]["slots"]["main"]["*"]
        return wt[:800]
    return "EMPTY"


titles = [
    "Honfidal",
    "Honfidal (Petőfi Sándor)",
    "Honfidal (Petőfi)",
    "Istentelen egy élet",
    "Nemzeti dal (Petőfi Sándor)",
]

for t in titles:
    print(f"\n=== {t} ===")
    result = fetch_raw(t)
    print(result[:400])
    time.sleep(0.5)
