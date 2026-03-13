#!/usr/bin/env python3
"""Try to find 'Istentelen egy élet' from MEK or other Hungarian poetry sites."""
import urllib.request
import re

urls = [
    "https://mek.oszk.hu/01000/01006/01006.htm",
    "https://magyar-irodalom. encyclopaedia.hu/petofi",
]

# Try MEK - Petőfi összes versei
try:
    url = "https://mek.oszk.hu/01000/01006/01006.htm"
    req = urllib.request.Request(url, headers={"User-Agent": "BibliotecaArion/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("iso-8859-2", errors="replace")
        # Search for istentelen
        idx = html.lower().find("istentelen")
        if idx >= 0:
            print(f"Found 'istentelen' at position {idx}")
            print(html[max(0,idx-200):idx+500])
        else:
            print("Not found in MEK main page")
            # Look for links
            links = re.findall(r'href="([^"]*istentelen[^"]*)"', html, re.IGNORECASE)
            if links:
                print(f"Found links: {links}")
except Exception as e:
    print(f"MEK error: {e}")

# Try searching MEK
try:
    url2 = "https://mek.oszk.hu/cgi-bin/mek.cgi?kereso=istentelen+petofi"
    req2 = urllib.request.Request(url2, headers={"User-Agent": "BibliotecaArion/1.0"})
    with urllib.request.urlopen(req2, timeout=30) as resp2:
        html2 = resp2.read().decode("utf-8", errors="replace")
        print(f"\nMEK search result length: {len(html2)}")
        if "istentelen" in html2.lower():
            print("Found in search results!")
except Exception as e:
    print(f"MEK search error: {e}")
