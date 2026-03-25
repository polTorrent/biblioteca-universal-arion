#!/usr/bin/env python3
"""Assemble translation from parts."""
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

with open("_part1_cat.md", "r") as f:
    part1 = f.read()

with open("_part2_cat.md", "r") as f:
    part2_lines = f.readlines()

part2_from_june19 = "".join(part2_lines[52:])

with open("_part3_cat.md", "r") as f:
    part3 = f.read()

with open("_part4a_cat.md", "r") as f:
    part4a = f.read()

with open("_part4b_cat.md", "r") as f:
    part4b = f.read()

with open("_part4c_cat.md", "r") as f:
    part4c = f.read()

header = "# Els sofriments del jove Werther\n"
header += "*Johann Wolfgang von Goethe*\n\n"
header += "Traduit de l'alemany per Biblioteca Arion\n\n---\n\n"

full = header + part1 + "\n\n" + part2_from_june19 + "\n\n" + part3 + "\n\n" + part4a + "\n\n" + part4b + "\n\n" + part4c

with open("traduccio.md", "w") as f:
    f.write(full)

lines = full.count("\n")
words = len(full.split())
print(f"Lines: {lines}, Words: {words}, Chars: {len(full)}")
