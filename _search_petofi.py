#!/usr/bin/env python3
"""Search Wikisource for correct Petőfi poem titles."""
import subprocess
import json
import urllib.parse
import time

API = "https://hu.wikisource.org/w/api.php"

searches = [
    "Az Alföld",
    "Fa leszek ha",
    "Honfidal",
    "Ha férfi vagy légy férfi",
    "Anyám tyúkja",
    "A bánat Egy nagy óceán",
    "Szabadság szerelem Petőfi",
    "A XIX század költői Petőfi",
    "Istentelen egy élet Petőfi",
]

for q in searches:
    params = urllib.parse.urlencode({
        "action": "query",
        "list": "search",
        "srsearch": q,
        "format": "json",
        "srlimit": 5,
    })
    url = f"{API}?{params}"
    result = subprocess.run(["curl", "-s", url], capture_output=True, text=True, timeout=30)
    data = json.loads(result.stdout)
    titles = [r["title"] for r in data["query"]["search"]]
    print(f"{q}: {titles}")
    time.sleep(0.5)
