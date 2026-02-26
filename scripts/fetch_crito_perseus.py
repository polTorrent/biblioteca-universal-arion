#!/usr/bin/env python3
"""Fetch Plato's Crito Greek text from Perseus Digital Library, section by section."""
import html
import re
import urllib.request
import time

BASE_URL = "https://www.perseus.tufts.edu/hopper/text?doc=Perseus%3Atext%3A1999.01.0169%3Atext%3DCrito%3Asection%3D{section}"

# Crito sections in Perseus: 43a through 54e
sections = []
for num in range(43, 55):
    for letter in "abcde":
        sections.append(f"{num}{letter}")

all_text = []

for section in sections:
    url = BASE_URL.format(section=section)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8", errors="replace")

        # Extract text from the primary source div
        # Perseus uses class="text_container" or similar
        # Let's look for Greek characters in the page
        match = re.search(r'class="text_container"[^>]*>(.*?)</div>', content, re.DOTALL)
        if match:
            chunk = match.group(1)
            chunk = re.sub(r"<[^>]+>", "", chunk)
            chunk = html.unescape(chunk).strip()
            if chunk:
                all_text.append(f"[{section}] {chunk}")
                print(f"OK {section}: {chunk[:80]}...")
            else:
                print(f"EMPTY {section}")
        else:
            # Try finding any substantial Greek text
            greek_pattern = re.compile(r'([\u0370-\u03FF\u1F00-\u1FFF].{20,})')
            found = greek_pattern.findall(content)
            if found:
                longest = max(found, key=len)
                all_text.append(f"[{section}] {longest}")
                print(f"GREP {section}: {longest[:80]}...")
            else:
                print(f"MISS {section}")

        time.sleep(0.5)  # Be polite
    except Exception as e:
        print(f"ERR {section}: {e}")

print("\n\n========== FULL TEXT ==========\n")
print("\n\n".join(all_text))
print(f"\n\nTotal sections found: {len(all_text)}")
