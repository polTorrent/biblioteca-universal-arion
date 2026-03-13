#!/usr/bin/env python3
"""Fetch Petőfi poems from Hungarian Wikisource and extract text."""
import html
import re
import subprocess
import sys
import time

POEMS = {
    "Nemzeti_dal": "Nemzeti dal",
    "Szeptember_végén": "Szeptember végén",
    "Egy_gondolat_bánt_engemet…": "Egy gondolat bánt engemet",
    "A_Tisza": "A Tisza",
    "Föltámadott_a_tenger": "Föltámadott a tenger",
    "Reszket_a_bokor,_mert…": "Reszket a bokor, mert...",
    "Az_alföld": "Az alföld",
    "Befordúltam_a_konyhára…": "Befordúltam a konyhára",
    "A_XIX._század_költői": "A XIX. század költői",
    "Fa_leszek,_ha…": "Fa leszek, ha...",
    "Minek_nevezzelek?": "Minek nevezzelek?",
    "Anyám_tyúkja": "Anyám tyúkja",
    "A_puszta,_télen": "A puszta, télen",
    "Itt_van_az_ősz,_itt_van_újra": "Itt van az ősz, itt van újra",
    "Ha_férfi_vagy,_légy_férfi": "Ha férfi vagy, légy férfi",
    "Dalaim": "Dalaim",
    "A_bánat?_egy_nagy_óceán": "A bánat? egy nagy óceán",
    "Szabadság,_szerelem!": "Szabadság, szerelem",
    "Honfidal": "Honfidal",
    "Istentelen_egy_élet…": "Istentelen egy élet",
}

BASE = "https://hu.wikisource.org/wiki/"


def fetch_page(slug: str) -> str:
    """Fetch a Wikisource page and return raw HTML."""
    url = BASE + slug
    result = subprocess.run(
        ["curl", "-s", "-L", url],
        capture_output=True, text=True, timeout=30
    )
    return result.stdout


def extract_poem(html_text: str) -> str:
    """Extract poem text from Wikisource HTML."""
    # Find the parser output div
    match = re.search(
        r'<div class="mw-parser-output">(.*?)(?:<div class="printfooter"|<div id="catlinks")',
        html_text, re.DOTALL
    )
    if not match:
        return ""

    content = match.group(1)

    # Remove navigation/header elements
    content = re.sub(r'<table[^>]*>.*?</table>', '', content, flags=re.DOTALL)
    content = re.sub(r'<div class="ws-noexport"[^>]*>.*?</div>', '', content, flags=re.DOTALL)
    content = re.sub(r'<div[^>]*class="[^"]*header[^"]*"[^>]*>.*?</div>', '', content, flags=re.DOTALL)
    content = re.sub(r'<div[^>]*style="[^"]*display:\s*none[^"]*"[^>]*>.*?</div>', '', content, flags=re.DOTALL)

    # Handle poem formatting: <br /> -> newline, </p> -> double newline
    content = re.sub(r'<br\s*/?>', '\n', content)
    content = re.sub(r'</p>', '\n\n', content)
    content = re.sub(r'</div>', '\n', content)

    # Remove remaining HTML tags
    content = re.sub(r'<[^>]+>', '', content)
    content = html.unescape(content)

    # Clean up whitespace
    lines = content.split('\n')
    lines = [l.strip() for l in lines]

    # Remove leading/trailing empty lines
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()

    # Collapse multiple blank lines into one
    result = []
    prev_blank = False
    for line in lines:
        if not line:
            if not prev_blank:
                result.append('')
                prev_blank = True
        else:
            result.append(line)
            prev_blank = False

    return '\n'.join(result)


def main():
    output_file = "/home/jo/biblioteca-universal-arion/_petofi_poems.md"
    results = {}

    for slug, title in POEMS.items():
        print(f"Fetching: {title} ({slug})...", file=sys.stderr)
        try:
            page_html = fetch_page(slug)
            poem_text = extract_poem(page_html)
            if poem_text and len(poem_text) > 20:
                results[title] = poem_text
                print(f"  OK ({len(poem_text)} chars)", file=sys.stderr)
            else:
                print(f"  EMPTY or too short, trying alternatives...", file=sys.stderr)
                # Try without special chars
                alt_slugs = [
                    slug.replace("…", ""),
                    slug.replace("…", "..."),
                    slug.replace(",_", "_"),
                    "Petőfi_Sándor_összes_költeményei/" + slug,
                ]
                for alt in alt_slugs:
                    page_html = fetch_page(alt)
                    poem_text = extract_poem(page_html)
                    if poem_text and len(poem_text) > 20:
                        results[title] = poem_text
                        print(f"  OK with alt slug: {alt} ({len(poem_text)} chars)", file=sys.stderr)
                        break
                    time.sleep(0.5)
                else:
                    results[title] = "NOT FOUND"
                    print(f"  NOT FOUND", file=sys.stderr)
        except Exception as e:
            results[title] = f"ERROR: {e}"
            print(f"  ERROR: {e}", file=sys.stderr)
        time.sleep(1)  # Be polite to Wikisource

    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Petőfi Sándor - Poemes originals en hongarès\n\n")
        f.write(f"Font: hu.wikisource.org (domini públic)\n\n")

        found = sum(1 for v in results.values() if v != "NOT FOUND" and not v.startswith("ERROR"))
        f.write(f"Poemes trobats: {found}/{len(POEMS)}\n\n")
        f.write("---\n\n")

        for title, text in results.items():
            f.write(f"## {title}\n\n")
            f.write(text)
            f.write("\n\n---\n\n")

    print(f"\nResults written to {output_file}", file=sys.stderr)
    print(f"Found {found}/{len(POEMS)} poems", file=sys.stderr)


if __name__ == "__main__":
    main()
