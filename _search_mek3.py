#!/usr/bin/env python3
"""Search for 'Istentelen egy élet' poem text from Hungarian poetry sites."""
import urllib.request
import re
import html as htmlmod

# Try versek.hu or similar poetry databases
urls = [
    ("https://www.arcanum.com/hu/online-kiadvanyok/Verstar-verstar-otven-kolto-osszes-verse-1/petofi-sandor-1822-1849-6425/", "arcanum"),
    ("https://hu.wikiquote.org/wiki/Petőfi_Sándor", "wikiquote"),
]

for url, name in urls:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BibliotecaArion/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8", errors="replace")
            idx = content.lower().find("istentelen")
            if idx >= 0:
                snippet = content[max(0,idx-200):idx+500]
                snippet = re.sub(r'<[^>]+>', '\n', snippet)
                snippet = htmlmod.unescape(snippet)
                lines = [l.strip() for l in snippet.split('\n') if l.strip()]
                print(f"Found at {name}:")
                print('\n'.join(lines[:20]))
            else:
                print(f"{name}: not found")
    except Exception as e:
        print(f"{name}: {e}")

# Try PIM (Petőfi Irodalmi Múzeum)
try:
    url3 = "https://pim.hu/"
    req3 = urllib.request.Request(url3, headers={"User-Agent": "BibliotecaArion/1.0"})
    with urllib.request.urlopen(req3, timeout=15) as resp3:
        print(f"\nPIM accessible: {resp3.status}")
except Exception as e:
    print(f"PIM: {e}")
