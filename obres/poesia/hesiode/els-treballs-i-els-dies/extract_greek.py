#!/usr/bin/env python3
"""Extract Greek text from Perseus TEI XML - no metadata headers."""
import xml.etree.ElementTree as ET
from pathlib import Path

xml_path = Path("obres/poesia/hesiode/els-treballs-i-els-dies/perseus_xml.xml")
tree = ET.parse(xml_path)
root = tree.getroot()

lines = []
for l_elem in root.iter("{http://www.tei-c.org/ns/1.0}l"):
    n = l_elem.get("n", "")
    text = "".join(l_elem.itertext()).strip()
    if text:
        lines.append(text)

output = Path("obres/poesia/hesiode/els-treballs-i-els-dies/original.md")
with open(output, "w", encoding="utf-8") as f:
    for line in lines:
        f.write(f"{line}\n")

print(f"Written {len(lines)} lines to original.md")
print(f"First: {lines[0]}")
print(f"Last: {lines[-1]}")
