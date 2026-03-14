#!/usr/bin/env python3
"""Parse Peri Hypsous wikitext and create original.md"""
import json
import re
import os

with open("peri_hypsous_raw.json", "r") as f:
    data = json.load(f)

wikitext = data["parse"]["wikitext"]["*"]

# Remove the header template
wikitext = re.sub(r"\{\{Κεφαλίδα.*?\}\}\n?", "", wikitext, flags=re.DOTALL)

# Remove image tags
wikitext = re.sub(r"\[\[Image:.*?\]\]", "", wikitext)

# Find all section markers
sections = re.findall(r"\{\{κ\|(\d+\.\d+)\}\}", wikitext)
chapter_nums = sorted(set(int(s.split(".")[0]) for s in sections))
print(f"Chapters found: {chapter_nums}")
print(f"Total section markers: {len(sections)}")


def replace_section(m):
    ref = m.group(1)
    chapter, para = ref.split(".")
    if para == "1":
        return f"\n\n## Capitol {chapter}\n\n**[{ref}]** "
    else:
        return f"\n\n**[{ref}]** "


wikitext = re.sub(r"\{\{κ\|(\d+\.\d+)\}\}", replace_section, wikitext)

# Remove remaining wiki templates
wikitext = re.sub(r"\{\{[^}]*\}\}", "", wikitext)

# Convert [[link|text]] to text, [[link]] to link
wikitext = re.sub(r"\[\[[^|\]]+\|([^\]]+)\]\]", r"\1", wikitext)
wikitext = re.sub(r"\[\[([^\]]+)\]\]", r"\1", wikitext)

# Replace <br> with newlines
wikitext = re.sub(r"<br\s*/?>", "\n", wikitext)

# Remove ref tags and content
wikitext = re.sub(r"<ref[^>]*>.*?</ref>", "", wikitext, flags=re.DOTALL)
wikitext = re.sub(r"<ref[^>]*/>", "", wikitext)

# Remove other HTML tags but keep content
wikitext = re.sub(r"</?[a-zA-Z][^>]*>", "", wikitext)

# Remove category links
wikitext = re.sub(r"\[\[Κατηγορία:[^\]]*\]\]", "", wikitext)

# Clean up whitespace
wikitext = re.sub(r"\n{3,}", "\n\n", wikitext)
wikitext = re.sub(r" +", " ", wikitext)
wikitext = wikitext.strip()

# Build the final markdown
md = (
    "# Peri hypsous (Del sublim)\n"
    "\n"
    "**Autor:** Pseudo-Longi (Longinos)\n"
    "**Epoca:** segle I dC (datacio disputada)\n"
    "**Llengua:** grec antic\n"
    "\n"
    "---\n"
    "\n"
    + wikitext
)

# Ensure directory exists
os.makedirs("obres/assaig/pseudo-longi/del-sublim", exist_ok=True)

# Write the file
with open("obres/assaig/pseudo-longi/del-sublim/original.md", "w") as f:
    f.write(md)

# Count words
word_count = len(re.findall(r"\S+", wikitext))
print(f"Words: {word_count}")
print(f"Chapters: {len(chapter_nums)}")
print("File written successfully")

# Preview
lines = md.split("\n")
print("\n--- FIRST 25 LINES ---")
for line in lines[:25]:
    print(line)
print("\n--- LAST 10 LINES ---")
for line in lines[-10:]:
    print(line)
