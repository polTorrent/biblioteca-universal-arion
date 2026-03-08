#!/usr/bin/env python3
"""Extreu el text llatí de De Rerum Natura (Llibre I) de l'HTML de The Latin Library."""

import re
import html

INPUT = "obres/filosofia/lucreci/de-rerum-natura-llibre-i/_lucretius1b.html"
OUTPUT = "obres/filosofia/lucreci/de-rerum-natura-llibre-i/original.md"

with open(INPUT, "r") as f:
    content = f.read()

# Extract body
body = re.search(r"<body[^>]*>(.*?)</body>", content, re.DOTALL | re.IGNORECASE)
text = body.group(1) if body else content

# Remove font tags (line numbers)
text = re.sub(r"<font[^>]*>.*?</font>", "", text, flags=re.IGNORECASE)
# Remove nbsp
text = text.replace("&nbsp;", "")
# Convert br to newlines
text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
# Convert p tags
text = re.sub(r"<p[^>]*>", "\n", text, flags=re.IGNORECASE)
text = re.sub(r"</p>", "", text, flags=re.IGNORECASE)
# Remove remaining HTML tags
text = re.sub(r"<[^>]+>", "", text)
# Unescape HTML
text = html.unescape(text)
# Clean up lines
lines = [l.rstrip() for l in text.split("\n")]
# Remove empty lines at start
while lines and not lines[0].strip():
    lines.pop(0)
# Remove empty lines at end
while lines and not lines[-1].strip():
    lines.pop()

# Remove the footer/navigation lines (The Latin Library, etc.)
clean_lines = []
for line in lines:
    if "The Latin Library" in line or "thelatinlibrary" in line:
        break
    clean_lines.append(line)

# Remove trailing empty lines after cleanup
while clean_lines and not clean_lines[-1].strip():
    clean_lines.pop()

# Build markdown
header = "# De Rerum Natura — Liber Primus\n\n"
header += "**Titus Lucretius Carus** (c. 99-55 aC)\n\n"
header += "Font: The Latin Library\n\n"
header += "---\n\n"

output = header + "\n".join(clean_lines) + "\n"

with open(OUTPUT, "w") as f:
    f.write(output)

print(f"Escrit: {len(output)} caràcters, {len(clean_lines)} línies")
print("Primers versos:")
for l in clean_lines[:5]:
    print(f"  {l}")
print("...")
print("Últims versos:")
for l in clean_lines[-5:]:
    print(f"  {l}")
