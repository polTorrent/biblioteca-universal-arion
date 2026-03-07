#!/usr/bin/env python3
"""Extract clean play text from Gutenberg scholarly edition."""
import re
import sys
import urllib.request

url = "https://www.gutenberg.org/cache/epub/23042/pg23042.txt"
with urllib.request.urlopen(url) as r:
    raw = r.read().decode("utf-8-sig")

# Extract between DRAMATIS and END marker
start = raw.find("DRAMATIS PERSONÆ")
end = raw.find("*** END OF THE PROJECT GUTENBERG")
if start == -1 or end == -1:
    print("Could not find markers", file=sys.stderr)
    sys.exit(1)

text = raw[start:end]

# Remove the GENERAL NOTES section at the end
general_notes = text.find("GENERAL NOTES")
if general_notes != -1:
    text = text[:general_notes]

# Remove footnote reference numbers [1], [2], etc. in the main text
text = re.sub(r'\[(\d+)\]', '', text)

# Remove Notes sections (lines starting with "Notes:" through next Scene or Act)
lines = text.split('\n')
clean_lines = []
in_notes = False
for line in lines:
    stripped = line.strip()
    # Detect start of notes section
    if stripped.startswith('Notes:') or stripped.startswith('Footnotes:'):
        in_notes = True
        continue
    # Detect end of notes section (new SCENE or ACT heading)
    if in_notes:
        if stripped.startswith('SCENE') or stripped.startswith('ACT') or stripped.startswith('DRAMATIS'):
            in_notes = False
        else:
            continue
    # Remove line number annotations at end of lines (e.g. "  5" or "  10")
    line = re.sub(r'\s+\d+\s*$', '', line)
    clean_lines.append(line)

result = '\n'.join(clean_lines)

# Clean up excessive blank lines
result = re.sub(r'\n{4,}', '\n\n\n', result)

print(result)
