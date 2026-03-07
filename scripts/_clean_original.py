#!/usr/bin/env python3
"""Neteja artefactes HTML/CSS de Wikisource d'un original.md."""
import re
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# Remove CSS blocks (.mw-parser-output...)
text = re.sub(r'^\.mw-parser-output[^\n]*\n?', '', text, flags=re.MULTILINE)

# Remove navigation lines (arrows)
text = re.sub(r'^←[^\n]*$', '', text, flags=re.MULTILINE)
text = re.sub(r'^[^\n]*→$', '', text, flags=re.MULTILINE)

# Remove "Συγγραφέας" line
text = re.sub(r'^Περὶ εὐθυμίας Συγγραφέας:[^\n]*$', '', text, flags=re.MULTILINE)

# Clean up multiple blank lines
text = re.sub(r'\n{3,}', '\n\n', text)

with open(path, "w", encoding="utf-8") as f:
    f.write(text.strip() + '\n')

print(f"Cleaned: {path} ({len(text)} chars)")
