import urllib.request
import urllib.parse
import re
import html

sonnets = [
    ("I", "Stepy akermańskie", "Sonety_Adama_Mickiewicza/Stepy_akermańskie"),
    ("II", "Cisza morska", "Sonety_Adama_Mickiewicza/Cisza_morska"),
    ("III", "Żegluga", "Sonety_Adama_Mickiewicza/Żegluga"),
    ("IV", "Burza", "Sonety_Adama_Mickiewicza/Burza"),
    ("V", "Widok gór ze stepów Kozłowa", "Sonety_Adama_Mickiewicza/Widok_gór_ze_stepów_Kozłowa"),
    ("VI", "Bakczysaraj", "Sonety_Adama_Mickiewicza/Bakczysaraj"),
    ("VII", "Bakczysaraj w nocy", "Sonety_Adama_Mickiewicza/Bakczysaraj_w_nocy"),
    ("VIII", "Grób Potockiéj", "Sonety_Adama_Mickiewicza/Grób_Potockiéj"),
    ("IX", "Mogiły Haremu", "Sonety_Adama_Mickiewicza/Mogiły_Haremu"),
    ("X", "Bajdary", "Sonety_Adama_Mickiewicza/Bajdary"),
    ("XI", "Ałuszta w dzień", "Sonety_Adama_Mickiewicza/Ałuszta_w_dzień"),
    ("XII", "Ałuszta w nocy", "Sonety_Adama_Mickiewicza/Ałuszta_w_nocy"),
    ("XIII", "Czatyrdah", "Sonety_Adama_Mickiewicza/Czatyrdah"),
    ("XIV", "Pielgrzym", "Sonety_Adama_Mickiewicza/Pielgrzym"),
    ("XV", "Droga nad przepaścią w Czufut-Kale", "Sonety_Adama_Mickiewicza/Droga_nad_przepaścią_w_Czufut-Kale"),
    ("XVI", "Góra Kikineis", "Sonety_Adama_Mickiewicza/Góra_Kikineis"),
    ("XVII", "Ruiny zamku w Bałakławie", "Sonety_Adama_Mickiewicza/Ruiny_zamku_w_Bałakławie"),
    ("XVIII", "Ajudah", "Sonety_Adama_Mickiewicza/Ajudah"),
]

def extract_poem(page_html, title):
    match = re.search(r'<div class="poem">(.*?)</div>\s*&#32;', page_html, re.DOTALL)
    if not match:
        match = re.search(r'<div class="poem">(.*?)</div>', page_html, re.DOTALL)
    if not match:
        return "ERROR: Could not find poem div"

    text = match.group(1)

    # Remove the roman numeral and title header lines
    # Remove <center> or <div class="center"> title blocks
    text = re.sub(r'<center>.*?</center>', '', text, flags=re.DOTALL)
    text = re.sub(r'<div class="center"[^>]*>.*?</div>', '', text, flags=re.DOTALL)

    # Remove footnote references
    text = re.sub(r'<sup[^>]*class="reference"[^>]*>.*?</sup>', '', text, flags=re.DOTALL)

    # Handle <span style="padding-left:..."> </span> (indentation spacers) - replace with spaces
    text = re.sub(r'<span style="padding-left:\d+px">\s*</span>', '    ', text)

    # Convert <br /> to newlines
    text = re.sub(r'<br\s*/?>', '\n', text)

    # Remove remaining HTML tags but preserve text content
    text = re.sub(r'<[^>]+>', '', text)

    # Unescape HTML entities
    text = html.unescape(text)

    # Clean up lines
    lines = text.split('\n')
    lines = [line.rstrip() for line in lines]

    # Remove empty lines at start and end
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    # Collapse multiple consecutive empty lines into single empty line (stanza break)
    result = []
    prev_empty = False
    for line in lines:
        if not line.strip():
            if not prev_empty:
                result.append('')
                prev_empty = True
        else:
            prev_empty = False
            result.append(line)

    return '\n'.join(result)

output_parts = ["# Sonety krymskie — Adam Mickiewicz\n"]

for num, title, slug in sonnets:
    encoded_slug = urllib.parse.quote(slug, safe='()_-/')
    url = f"https://pl.wikisource.org/wiki/{encoded_slug}"
    print(f"Fetching {num}. {title}...", flush=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            page = resp.read().decode("utf-8")
        poem = extract_poem(page, title)
        output_parts.append(f"## {num}. {title}\n\n{poem}\n")
        line_count = len([l for l in poem.split('\n') if l.strip()])
        print(f"  OK ({line_count} non-empty lines)", flush=True)
        if line_count < 10:
            print(f"  WARNING: low line count, poem text:\n{poem[:200]}", flush=True)
    except Exception as e:
        print(f"  ERROR: {e}")
        output_parts.append(f"## {num}. {title}\n\nERROR: {e}\n")

output = '\n'.join(output_parts) + '\n'

with open("/home/jo/biblioteca-universal-arion/tmp_sonnets.md", "w") as f:
    f.write(output)

print("\nDone!")
