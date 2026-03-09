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

def extract_poem(page_html):
    # Find <div class="poem"> content
    match = re.search(r'<div class="poem">(.*?)</div>', page_html, re.DOTALL)
    if not match:
        return "ERROR: Could not find poem div"

    text = match.group(1)

    # Remove the roman numeral header and title (center/b tags at start)
    # Remove <center> lines (title lines)
    text = re.sub(r'<center>.*?</center>', '', text, flags=re.DOTALL)

    # Remove footnote references like [1]
    text = re.sub(r'<sup[^>]*class="reference"[^>]*>.*?</sup>', '', text, flags=re.DOTALL)

    # Convert <br /> to newlines
    text = re.sub(r'<br\s*/?>', '\n', text)

    # Remove remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Unescape HTML entities
    text = html.unescape(text)

    # Clean up lines
    lines = text.split('\n')
    # Strip trailing whitespace from each line
    lines = [line.rstrip() for line in lines]

    # Remove empty lines at start and end
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    return '\n'.join(lines)

output_parts = ["# Sonety krymskie — Adam Mickiewicz\n"]

for num, title, slug in sonnets:
    encoded_slug = urllib.parse.quote(slug, safe='()_-/')
    url = f"https://pl.wikisource.org/wiki/{encoded_slug}"
    print(f"Fetching {num}. {title}...", flush=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            page = resp.read().decode("utf-8")
        poem = extract_poem(page)
        output_parts.append(f"\n## {num}. {title}\n\n{poem}\n")
        line_count = len([l for l in poem.split('\n') if l.strip()])
        print(f"  OK ({line_count} non-empty lines)", flush=True)
    except Exception as e:
        print(f"  ERROR: {e}")
        output_parts.append(f"\n## {num}. {title}\n\nERROR: {e}\n")

output = '\n'.join(output_parts)

with open("/home/jo/biblioteca-universal-arion/tmp_sonnets.md", "w") as f:
    f.write(output)

print("\nDone!")
