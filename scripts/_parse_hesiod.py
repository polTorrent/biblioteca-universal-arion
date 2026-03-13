import re
import html as h

with open("/tmp/hesiod_perseus.xml", "r", encoding="utf-8") as f:
    xml = f.read()

# Extract only Greek lines (skip metadata)
lines = re.findall(r'<l[^>]*>(.*?)</l>', xml, re.DOTALL)
clean_lines = []
for line in lines:
    clean = re.sub(r'<[^>]+>', '', line)
    clean = h.unescape(clean).strip()
    if clean and not clean.startswith(('Greek', 'English', 'Basic', 'Text key', 'Check', 'Revise', 'Fix', 'converted')):
        # Only keep lines with Greek chars
        if re.search(r'[\u0370-\u03FF\u1F00-\u1FFF]', clean):
            clean_lines.append(clean)

print(f"Total Greek lines: {len(clean_lines)}")

# Also extract card/section markers
cards = re.findall(r'<milestone[^>]*unit="card"[^>]*n="(\d+)"', xml)
print(f"Card markers: {cards}")

# Build the text with line numbers
output_lines = []
for i, line in enumerate(clean_lines, 1):
    output_lines.append(line)

# Save
dest = "obres/poesia/hesiode/els-treballs-i-els-dies/original.md"
with open(dest, "w", encoding="utf-8") as f:
    f.write("# Ἔργα καὶ Ἡμέραι\n\n")
    f.write("**Ἡσίοδος** (Hesiod, s. VIII-VII aC)\n\n")
    f.write("Font: Perseus Digital Library (CC BY-SA 3.0)\n\n")
    f.write("---\n\n")
    for line in output_lines:
        f.write(line + "\n")

print(f"Written {len(output_lines)} lines to {dest}")
print("\nFirst 10 lines:")
for l in output_lines[:10]:
    print(l)
print("\nLast 5 lines:")
for l in output_lines[-5:]:
    print(l)
