#!/usr/bin/env python3
"""Neteja artefactes HTML/CSS de Wikisource d'un original.md."""
import re
import sys


def clean_original(path: str) -> None:
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

    text = text.strip() + '\n'
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"Cleaned: {path} ({len(text)} chars)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Ús: {sys.argv[0]} <fitxer>", file=sys.stderr)
        sys.exit(1)
    clean_original(sys.argv[1])
