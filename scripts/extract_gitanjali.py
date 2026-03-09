#!/usr/bin/env python3
"""Extract 30 selected poems from Gitanjali raw text."""
import re

with open("/home/jo/biblioteca-universal-arion/gitanjali_raw.txt", "r") as f:
    lines = f.read().split("\n")

# Find poem start lines
poem_starts = []
for i, line in enumerate(lines):
    m = re.match(r"^(\d+)\.$", line.strip())
    if m and int(m.group(1)) <= 103:
        poem_starts.append((i, int(m.group(1))))

# Extract each poem
poems = {}
for idx, (start_line, num) in enumerate(poem_starts):
    if idx + 1 < len(poem_starts):
        end_line = poem_starts[idx + 1][0]
    else:
        end_line = start_line + 50
        for j in range(start_line, min(start_line + 100, len(lines))):
            if "***" in lines[j] or "End of" in lines[j]:
                end_line = j
                break
    poem_text = "\n".join(lines[start_line + 1 : end_line]).strip("\n").strip()
    poems[num] = poem_text

# 30 most representative poems
selected = [
    1, 2, 3, 4, 5, 7, 10, 11, 12, 13,
    16, 22, 23, 27, 30, 34, 35, 36, 39, 45,
    48, 50, 56, 59, 67, 69, 72, 86, 96, 103,
]

output = []
output.append("# Gitanjali (Song Offerings)")
output.append("## Rabindranath Tagore (1912)")
output.append("")
output.append(
    "*Seleccio de 30 poemes de l'edicio anglesa de 1912, "
    "traduida pel propi autor del bengali original.*"
)
output.append("*Text de domini public -- Font: Project Gutenberg (ebook #7164)*")
output.append("")
output.append("---")
output.append("")

word_count = 0
for num in selected:
    output.append(f"### {num}.")
    output.append("")
    output.append(poems[num])
    output.append("")
    output.append("---")
    output.append("")
    word_count += len(poems[num].split())

target = "/home/jo/biblioteca-universal-arion/obres/poesia/rabindranath-tagore/gitanjali-seleccio-30-poemes/original.md"
with open(target, "w") as f:
    f.write("\n".join(output))

print(f"Total poems found: {len(poems)}")
print(f"Selected: {len(selected)}")
print(f"Word count: {word_count}")
print("original.md written successfully")
