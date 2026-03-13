#!/usr/bin/env python3
"""Search for Istentelen egy élet on various sources."""
import json
import urllib.parse
import urllib.request

API = "https://hu.wikisource.org/w/api.php"

# List all Petőfi pages on Wikisource containing "istentelen" or "Istentelen"
params = urllib.parse.urlencode({
    "action": "query",
    "list": "search",
    "srsearch": "istentelen Petőfi",
    "format": "json",
    "srlimit": 10,
})
url = f"{API}?{params}"
req = urllib.request.Request(url, headers={"User-Agent": "BibliotecaArion/1.0"})
with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    print("Search 'istentelen Petőfi':")
    for r in data["query"]["search"]:
        print(f"  {r['title']}")

print()

# Also try category listing
params2 = urllib.parse.urlencode({
    "action": "query",
    "list": "categorymembers",
    "cmtitle": "Kategória:Petőfi Sándor",
    "cmlimit": 500,
    "format": "json",
})
url2 = f"{API}?{params2}"
req2 = urllib.request.Request(url2, headers={"User-Agent": "BibliotecaArion/1.0"})
with urllib.request.urlopen(req2, timeout=30) as resp2:
    data2 = json.loads(resp2.read().decode("utf-8"))
    print("All Petőfi works on Wikisource:")
    for m in data2["query"]["categorymembers"]:
        title = m["title"]
        if "istentelen" in title.lower() or "isten" in title.lower():
            print(f"  ** {title}")
        else:
            print(f"  {title}")
