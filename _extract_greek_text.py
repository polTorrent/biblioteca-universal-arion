#!/usr/bin/env python3
"""Extract Greek text from downloaded Wikisource HTML files."""
import re
import html as html_mod

output_dir = "/home/jo/biblioteca-universal-arion"

def extract_text_from_html(html_content):
    """Extract the main text content from a Wikisource page."""
    # Find the content area - mw-content-ltr mw-parser-output
    match = re.search(r'mw-parser-output"[^>]*>(.*)', html_content, re.DOTALL)
    if not match:
        return "ERROR: Could not find content area"

    content = match.group(1)

    # Cut at printfooter or catlinks
    for cutoff in ['<div class="printfooter"', '<div id="catlinks"', '<!-- NewPP']:
        idx = content.find(cutoff)
        if idx > 0:
            content = content[:idx]
            break

    # Remove header template table
    content = re.sub(r'<table[^>]*>.*?</table>', '', content, flags=re.DOTALL)

    # Remove script and style tags
    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
    content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)

    # Remove edit section links
    content = re.sub(r'<span class="mw-editsection">.*?</span>\s*</span>', '', content, flags=re.DOTALL)

    # Remove navigation/noexport divs
    content = re.sub(r'<div[^>]*class="[^"]*ws-noexport[^"]*"[^>]*>.*?</div>', '', content, flags=re.DOTALL)
    content = re.sub(r'<div[^>]*class="[^"]*noprint[^"]*"[^>]*>.*?</div>', '', content, flags=re.DOTALL)

    # Convert <li> tags to numbered items
    li_count = [0]
    def replace_li(m):
        li_count[0] += 1
        return f"\n{li_count[0]}. "
    content = re.sub(r'<li[^>]*>', lambda m: replace_li(m), content)

    # Convert <br> to newlines
    content = re.sub(r'<br\s*/?>', '\n', content)

    # Convert headings
    content = re.sub(r'<h[1-6][^>]*>(.*?)</h[1-6]>', r'\n\n### \1\n\n', content, flags=re.DOTALL)

    # Convert paragraph ends to double newlines
    content = re.sub(r'</p>', '\n\n', content)

    # Remove all remaining HTML tags
    content = re.sub(r'<[^>]+>', '', content)

    # Decode HTML entities
    content = html_mod.unescape(content)

    # Clean up whitespace
    content = re.sub(r'[ \t]+', ' ', content)
    content = re.sub(r' *\n *', '\n', content)
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = content.strip()

    return content


all_text = []

for book_num in range(1, 13):
    filepath = f"{output_dir}/_wikisource_book_{book_num}.html"
    print(f"Processing Book {book_num}...")

    with open(filepath, 'r', encoding='utf-8') as f:
        html_content = f.read()

    text = extract_text_from_html(html_content)
    all_text.append(f"# ΒΙΒΛΙΟΝ {book_num} (Book {book_num})\n\n{text}")
    print(f"  Extracted {len(text)} characters")

# Write combined output
output_file = f"{output_dir}/_meditations_greek_full.txt"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("# Μάρκου Αὐρηλίου Ἀντωνίνου - Τὰ εἰς ἑαυτόν\n")
    f.write("# Marcus Aurelius Antoninus - Meditations (Greek Text)\n")
    f.write("# Source: Greek Wikisource (el.wikisource.org)\n\n")
    f.write("\n\n".join(all_text))

print(f"\nFull text written to {output_file}")
