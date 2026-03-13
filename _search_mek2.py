#!/usr/bin/env python3
"""Search MEK for Petőfi poems index page."""
import urllib.request
import re
import html

# MEK Petőfi összes költeményei - table of contents
urls_to_try = [
    "https://mek.oszk.hu/01000/01006/html/index.htm",
    "https://mek.oszk.hu/01000/01006/",
    "https://mek.oszk.hu/01000/01006/html/",
]

for url in urls_to_try:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BibliotecaArion/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("iso-8859-2", errors="replace")
            idx = content.lower().find("istentelen")
            if idx >= 0:
                snippet = content[max(0,idx-100):idx+300]
                snippet = re.sub(r'<[^>]+>', ' ', snippet)
                snippet = html.unescape(snippet)
                print(f"Found at {url}:")
                print(snippet.strip())
                # Find the link
                links = re.findall(r'href="([^"]*)"[^>]*>[^<]*istentelen[^<]*</a>', content, re.IGNORECASE)
                if links:
                    print(f"Link: {links}")
            else:
                print(f"{url}: not found (page size: {len(content)})")
    except Exception as e:
        print(f"{url}: {e}")
