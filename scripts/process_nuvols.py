#!/usr/bin/env python3
"""Process Wikisource JSON for Els núvols and create original.md"""
import json
import re
import os


def process_nuvols(input_path: str, outpath: str) -> None:
    with open(input_path, encoding="utf-8") as f:
        d = json.load(f)

    text: str = d["parse"]["wikitext"]["*"]

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

    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    with open(outpath, "w", encoding="utf-8") as f:
        f.write(header + text)

    size = os.path.getsize(outpath)
    with open(outpath, encoding="utf-8") as f:
        lines = sum(1 for _ in f)
    print(f"original.md: {size} bytes, {lines} lines")


if __name__ == "__main__":
    process_nuvols(
        input_path="/tmp/nuvols_wiki.json",
        outpath="obres/teatre/aristofanes/els-nuvols/original.md",
    )
