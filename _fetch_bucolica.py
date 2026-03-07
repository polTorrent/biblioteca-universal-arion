#!/usr/bin/env python3
"""Fetch Virgil's Bucolica from The Latin Library and save as original.md"""
import urllib.request
import re
import html

BASE_URL = "https://www.thelatinlibrary.com/vergil/ec{}.shtml"
OUTPUT = "obres/poesia/virgili/bucoliques/original.md"

eclogues = []

for i in range(1, 11):
    url = BASE_URL.format(i)
    print(f"Fetching Eclogue {i} from {url}...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=30)
        raw = resp.read().decode("latin-1")

        # Extract text between <p> tags (the poem content)
        # Remove HTML tags but keep line breaks
        # The Latin Library uses simple HTML
        body = re.search(r'<body[^>]*>(.*?)</body>', raw, re.DOTALL)
        if body:
            content = body.group(1)
            # Remove navigation, headers etc - keep poem text
            # Remove script tags
            content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
            # Remove style tags
            content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
            # Convert <br> to newlines
            content = re.sub(r'<br\s*/?>', '\n', content)
            # Convert </p> to double newlines
            content = re.sub(r'</p>', '\n\n', content)
            # Remove all other HTML tags
            content = re.sub(r'<[^>]+>', '', content)
            # Decode HTML entities
            content = html.unescape(content)
            # Clean up whitespace
            lines = [line.rstrip() for line in content.split('\n')]
            content = '\n'.join(lines).strip()
            # Remove excessive blank lines
            content = re.sub(r'\n{3,}', '\n\n', content)
            eclogues.append((i, content))
            print(f"  OK ({len(content)} chars)")
        else:
            print(f"  WARNING: no body found")
    except Exception as e:
        print(f"  ERROR: {e}")

if not eclogues:
    print("ERROR: No eclogues fetched!")
    exit(1)

# Build the markdown file
md = """# Bucòliques (Eclogae)

**Autor**: Publius Vergilius Maro (Virgili)
**Llengua original**: Llatí
**Data**: c. 42-39 aC
**Font**: [The Latin Library](https://www.thelatinlibrary.com/vergil.html)

---

"""

for num, text in eclogues:
    md += f"## Ecloga {num}\n\n{text}\n\n---\n\n"

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(md)

print(f"\nWritten {len(md)} chars to {OUTPUT}")
print(f"Eclogues fetched: {len(eclogues)}/10")
