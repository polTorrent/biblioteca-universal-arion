#!/usr/bin/env python3
import json, urllib.request, urllib.parse

cont = ""
all_pages = []
for i in range(10):
    p = {
        "action": "query",
        "list": "allpages",
        "apprefix": "Decameron/",
        "aplimit": "500",
        "format": "json",
    }
    if cont:
        p["apcontinue"] = cont
    params = urllib.parse.urlencode(p)
    url = "https://it.wikisource.org/w/api.php?" + params
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read())
    pages = data.get("query", {}).get("allpages", [])
    all_pages.extend(pages)
    c = data.get("continue", {}).get("apcontinue", "")
    if not c:
        break
    cont = c

novellas = [p["title"] for p in all_pages if "Novella" in p["title"]]
for n in novellas:
    print(n)
print(f"\nTotal: {len(novellas)} novellas, {len(all_pages)} total pages")
