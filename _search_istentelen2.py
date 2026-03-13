#!/usr/bin/env python3
"""Search for 'Istentelen egy élet' - the actual poem title might differ."""
import urllib.request
import urllib.parse
import json
import re
import html as htmlmod

# The poem might be known by a different title.
# "Istentelen egy élet ez" or "Istentelen élet" are possibilities.
# Let's check Hungarian wikiquote properly

url = "https://hu.wikiquote.org/w/api.php?" + urllib.parse.urlencode({
    "action": "query",
    "titles": "Petőfi Sándor",
    "prop": "revisions",
    "rvprop": "content",
    "rvslots": "main",
    "format": "json",
})
try:
    req = urllib.request.Request(url, headers={"User-Agent": "BibliotecaArion/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        pages = data["query"]["pages"]
        for pid, page in pages.items():
            content = page["revisions"][0]["slots"]["main"]["*"]
            idx = content.lower().find("istentelen")
            if idx >= 0:
                print("Found in Wikiquote!")
                print(content[max(0,idx-100):idx+500])
            else:
                print(f"Not found in Wikiquote (page size: {len(content)})")
except Exception as e:
    print(f"Wikiquote error: {e}")

# The poem's actual first line is:
# "Istentelen egy élet ez!"
# Let's search for this exact phrase
print("\nSearching Wikisource for 'Istentelen egy élet ez'...")
search_url = "https://hu.wikisource.org/w/api.php?" + urllib.parse.urlencode({
    "action": "query",
    "list": "search",
    "srsearch": '"istentelen egy élet"',
    "format": "json",
    "srlimit": 10,
})
try:
    req2 = urllib.request.Request(search_url, headers={"User-Agent": "BibliotecaArion/1.0"})
    with urllib.request.urlopen(req2, timeout=30) as resp2:
        data2 = json.loads(resp2.read().decode("utf-8"))
        results = data2["query"]["search"]
        if results:
            for r in results:
                print(f"  {r['title']}")
        else:
            print("  No results")
except Exception as e:
    print(f"  Error: {e}")
