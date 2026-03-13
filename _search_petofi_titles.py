#!/usr/bin/env python3
"""Search Wikisource Petőfi category for poems starting with 'I'."""
import urllib.request
import urllib.parse
import json

API = "https://hu.wikisource.org/w/api.php"

params = urllib.parse.urlencode({
    "action": "query",
    "list": "categorymembers",
    "cmtitle": "Kategória:Petőfi Sándor",
    "cmlimit": 500,
    "cmstartsortkeyprefix": "I",
    "format": "json",
})
url = f"{API}?{params}"
req = urllib.request.Request(url, headers={"User-Agent": "BibliotecaArion/1.0"})
with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    for m in data["query"]["categorymembers"]:
        t = m["title"]
        if t.lower().startswith("i") or t.lower().startswith("í"):
            print(t)
