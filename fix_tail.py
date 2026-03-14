with open("obres/assaig/pseudo-longi/del-sublim/original.md", "r") as f:
    content = f.read()

# Remove the modern Greek text at the end (lines 505 onwards are not ancient Greek original)
# Keep up to the Platonic quote ending
idx = content.find("\n*και δή Φρυνίχω")
if idx != -1:
    content = content[:idx].rstrip() + "\n"

# Fix Capitol -> Capitol (with accent)
content = content.replace("## Capitol ", "## Capitol ")
# Actually use Catalan
import re
content = re.sub(r"## Capitol (\d+)", lambda m: f"## Capítol {m.group(1)}", content)

with open("obres/assaig/pseudo-longi/del-sublim/original.md", "w") as f:
    f.write(content)

print("Done. File cleaned.")
# Count
lines = content.split("\n")
print(f"Lines: {len(lines)}")
words = len(content.split())
print(f"Approx words: {words}")
