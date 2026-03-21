import os
import sys

d = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "obres", "teatre", "henrik-ibsen", "et-dukkehjem-casa-de-nines"
)

parts = []
for fname in ["act1_ca.md", "act2_ca.md", "act3_ca.md"]:
    with open(os.path.join(d, fname), "r") as f:
        parts.append(f.read())

combined = parts[0] + "\n" + parts[1] + "\n" + parts[2]

filtered_lines = []
for line in combined.split("\n"):
    if line.startswith("[ERROR:"):
        continue
    if "CLI ha retornat" in line:
        continue
    if "Claude CLI ha fallat" in line:
        continue
    filtered_lines.append(line)

result = "\n".join(filtered_lines)

outpath = os.path.join(d, "traduccio.md")
with open(outpath, "w") as f:
    f.write(result)

print("Written to", outpath)
print("Total lines:", result.count("\n"))
