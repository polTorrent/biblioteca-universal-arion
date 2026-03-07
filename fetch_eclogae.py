import urllib.request
import html
import re
import os

numerals = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]

def extract_poem_text(html_content):
    """Extract the poem text from a Wikisource ecloga page."""
    # Find the main content area - look for the poem div
    # Try to find content between the header info and the categories
    text = re.sub(r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", html_content, flags=re.DOTALL)

    # Find the poem section - usually in a div with class "poem" or similar
    poem_match = re.search(r'<div class="poem">(.*?)</div>', html_content, re.DOTALL)
    if poem_match:
        poem_html = poem_match.group(1)
        # Clean HTML tags
        poem_text = re.sub(r"<br\s*/?>", "\n", poem_html)
        poem_text = re.sub(r"<[^>]+>", "", poem_text)
        poem_text = html.unescape(poem_text)
        return poem_text.strip()

    # Alternative: look for the mw-parser-output content
    content_match = re.search(r'class="mw-parser-output">(.*?)<div class="printfooter"', html_content, re.DOTALL)
    if content_match:
        content_html = content_match.group(1)
        # Remove navigation, header templates, etc.
        content_html = re.sub(r'<table[^>]*>.*?</table>', '', content_html, flags=re.DOTALL)
        content_html = re.sub(r'<div class="ws-noexport[^"]*"[^>]*>.*?</div>', '', content_html, flags=re.DOTALL)
        # Convert br to newlines
        content_html = re.sub(r"<br\s*/?>", "\n", content_html)
        # Remove remaining tags
        content_html = re.sub(r"<[^>]+>", "", content_html)
        content_html = html.unescape(content_html)
        lines = [l.strip() for l in content_html.split("\n")]
        # Filter out empty lines at start/end, keep structure
        while lines and not lines[0]:
            lines.pop(0)
        while lines and not lines[-1]:
            lines.pop()
        return "\n".join(lines)

    return None

all_text = []

for num in numerals:
    url = f"https://la.wikisource.org/wiki/Ecloga_{num}"
    print(f"Fetching Ecloga {num}...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read().decode("utf-8")

        poem = extract_poem_text(content)
        if poem:
            all_text.append(f"## Ecloga {num}\n\n{poem}")
            print(f"  OK ({len(poem)} chars)")
        else:
            print(f"  WARNING: Could not extract text")
            # Save raw for debugging
            with open(f"ecloga_{num}_raw.html", "w") as f:
                f.write(content)
    except Exception as e:
        print(f"  ERROR: {e}")

if all_text:
    output = "# Bucolica (Eclogae)\n\n**Publius Vergilius Maro** (70–19 aC)\n\n---\n\n" + "\n\n---\n\n".join(all_text) + "\n"

    os.makedirs("obres/poesia/virgili/bucoliques", exist_ok=True)
    with open("obres/poesia/virgili/bucoliques/original.md", "w") as f:
        f.write(output)

    print(f"\nDone! Wrote {len(all_text)} eclogues to obres/poesia/virgili/bucoliques/original.md")
else:
    print("\nERROR: No eclogues extracted!")
