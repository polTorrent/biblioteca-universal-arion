#!/usr/bin/env python3
"""Process Wikisource JSON for Els núvols and create original.md"""
import json
import re
import os

with open("/tmp/nuvols_wiki.json") as f:
    d = json.load(f)

text = d["parse"]["wikitext"]["*"]

# Remove wiki templates
text = re.sub(r"\{\{[^}]*\}\}", "", text)
# Remove category links
text = re.sub(r"\[\[Κατηγορία:[^\]]*\]\]", "", text)
# Remove other wiki links, keep display text
text = re.sub(r"\[\[[^|\]]*\|([^\]]*)\]\]", r"\1", text)
text = re.sub(r"\[\[([^\]]*)\]\]", r"\1", text)
# Convert <poem> tags
text = text.replace("<poem>", "").replace("</poem>", "")
# Convert bold wiki markup
text = re.sub(r"'''([^']+)'''", r"**\1**", text)
# Clean up headers
text = re.sub(r"==+\s*", "## ", text)
text = re.sub(r"\s*==+", "", text)
# Clean excessive whitespace
text = re.sub(r"\n{3,}", "\n\n", text)
text = text.strip()

header = """# Νεφέλαι (Els núvols)

**Autor:** Ἀριστοφάνης (Aristòfanes)
**Data:** 423 aC (primera versió), c. 419-416 aC (revisió)
**Llengua original:** grec antic
**Font:** Wikisource (el.wikisource.org)
**Llicència:** Domini públic

---

"""

outpath = "obres/teatre/aristofanes/els-nuvols/original.md"
with open(outpath, "w") as f:
    f.write(header + text)

size = os.path.getsize(outpath)
lines = sum(1 for _ in open(outpath))
print(f"original.md: {size} bytes, {lines} lines")
