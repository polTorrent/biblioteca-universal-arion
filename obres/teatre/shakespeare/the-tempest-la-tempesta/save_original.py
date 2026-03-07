#!/usr/bin/env python3
"""Extract clean play text and save original.md + per-act files."""
import re
import urllib.request

url = "https://www.gutenberg.org/cache/epub/23042/pg23042.txt"
with urllib.request.urlopen(url) as r:
    raw = r.read().decode("utf-8-sig")

start = raw.find("DRAMATIS PERSON")
end = raw.find("*** END OF THE PROJECT GUTENBERG")
text = raw[start:end]

# Remove GENERAL NOTES section
gn = text.find("GENERAL NOTES")
if gn != -1:
    text = text[:gn]

# Remove footnote refs [1], [2] etc.
text = re.sub(r"\[(\d+)\]", "", text)

# Remove Notes/Footnotes sections
lines = text.split("\n")
clean = []
in_notes = False
for line in lines:
    s = line.strip()
    if s.startswith("Notes:") or s.startswith("Footnotes:"):
        in_notes = True
        continue
    if in_notes:
        if s.startswith("SCENE") or s.startswith("ACT") or s.startswith("THE TEMPEST"):
            in_notes = False
        else:
            continue
    # Remove trailing line numbers
    line = re.sub(r"\s+\d+\s*$", "", line)
    clean.append(line)

result = "\n".join(clean)
result = re.sub(r"\n{4,}", "\n\n\n", result)

base = "obres/teatre/shakespeare/the-tempest-la-tempesta"

# Save full original
with open(f"{base}/original.md", "w") as f:
    f.write(result.strip() + "\n")

# Split by ACT headings and save individual files
acts = re.split(r"(ACT [IVX]+\.)", result)
for i in range(1, len(acts), 2):
    act_num = acts[i].strip().replace("ACT ", "").replace(".", "")
    act_content = acts[i] + (acts[i + 1] if i + 1 < len(acts) else "")
    with open(f"{base}/act_{act_num}.txt", "w") as f:
        f.write(act_content.strip() + "\n")
    print(f"Saved act_{act_num}.txt")

print("Done - original.md created")
