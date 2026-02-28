"""Integrate Zweites+Drittes Buch into original.md after Erstes Buch."""
import os

DIR = "/home/jo/biblioteca-universal-arion/obres/filosofia/nietzsche/aurora/"

# Read existing original.md
with open(os.path.join(DIR, "original.md"), "r", encoding="utf-8") as f:
    original = f.read()

# Read the new Zweites+Drittes Buch content
with open(os.path.join(DIR, "_zweites_drittes_buch.md"), "r", encoding="utf-8") as f:
    new_content = f.read()

# Find the insertion point: after the end of Erstes Buch (aphorism 96),
# before the --- divider and Fünftes Buch
# The structure is:
#   ...aphorism 96 text...\n\n\n---\n\n\n## Fünftes Buch
marker = "\n\n---\n\n\n## Fünftes Buch"
pos = original.find(marker)
if pos == -1:
    # Try alternative spacing
    marker = "\n---\n\n\n## Fünftes Buch"
    pos = original.find(marker)
if pos == -1:
    marker = "\n\n\n---\n\n\n## Fünftes Buch"
    pos = original.find(marker)

if pos == -1:
    print("ERROR: Could not find insertion point!")
    print("Looking for '---' followed by '## Fünftes Buch'")
    # Try to find them separately
    idx_divider = original.find("---\n")
    idx_funftes = original.find("## Fünftes Buch")
    print(f"  '---' at position: {idx_divider}")
    print(f"  '## Fünftes Buch' at position: {idx_funftes}")

    if idx_divider > 0 and idx_funftes > idx_divider:
        # Replace from the --- to just before ## Fünftes Buch
        before = original[:idx_divider].rstrip()
        after = original[idx_funftes:]
        result = before + "\n" + new_content + "\n\n---\n\n" + after
        print(f"Used fallback method. Writing result...")
    else:
        exit(1)
else:
    before = original[:pos].rstrip()
    after = original[pos + len(marker):]
    # Construct: before + new_content + divider + Fünftes Buch + after
    result = before + "\n" + new_content + "\n\n---\n\n## Fünftes Buch" + after

# Write the result
with open(os.path.join(DIR, "original.md"), "w", encoding="utf-8") as f:
    f.write(result)

print(f"Done! original.md updated.")
print(f"Total characters: {len(result)}")

# Verify
line_count = result.count('\n') + 1
aph_count = result.count('### ')
print(f"Total lines: {line_count}")
print(f"Total aphorism headers: {aph_count}")
