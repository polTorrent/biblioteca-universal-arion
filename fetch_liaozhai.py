"""Fetch 10 famous stories from Liaozhai Zhiyi from Chinese Wikisource."""
import re
import time
import urllib.request
from urllib.parse import quote, unquote
from html.parser import HTMLParser

BASE = "https://zh.wikisource.org/wiki/%E8%81%8A%E9%BD%8B%E5%BF%97%E7%95%B0"

# 10 most famous stories with their volume and anchor
STORIES = [
    ("第01卷", "畫壁", "La paret pintada"),
    ("第01卷", "勞山道士", "El taoista del mont Lao"),
    ("第01卷", "嬌娜", "Jiaona"),
    ("第01卷", "王六郎", "Wang Liulang"),
    ("第01卷", "種梨", "Plantar peres"),
    ("第02卷", "聶小倩", "Nie Xiaoqian"),
    ("第02卷", "嬰寧", "Yingning"),
    ("第04卷", "促織", "El grill"),
    ("第05卷", "阿寶", "A Bao"),
    ("第06卷", "席方平", "Xi Fangping"),
]

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_content = False
        self.capture = False
        self.depth = 0
        self.text_parts = []
        self.skip_tags = {'script', 'style', 'sup', 'table'}
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if attrs_dict.get('id') == 'mw-content-text':
            self.in_content = True
            self.depth = 0
        if self.in_content:
            self.depth += 1
            if tag in self.skip_tags:
                self.skip_depth += 1
            if tag == 'br':
                self.text_parts.append('\n')
            if tag == 'p':
                self.text_parts.append('\n')

    def handle_endtag(self, tag):
        if self.in_content:
            self.depth -= 1
            if tag in self.skip_tags and self.skip_depth > 0:
                self.skip_depth -= 1
            if self.depth <= 0:
                self.in_content = False

    def handle_data(self, data):
        if self.in_content and self.skip_depth == 0:
            self.text_parts.append(data)

    def get_text(self):
        return ''.join(self.text_parts)


def fetch_volume(volume):
    url = f"{BASE}/{quote(volume)}"
    print(f"  Fetching {url}")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode('utf-8')


def extract_story(html_content, story_name, next_story_anchors=None):
    """Extract a story section from a volume page by its anchor."""
    # Find the story header
    pattern = f'id="{re.escape(story_name)}"'
    match = re.search(pattern, html_content)
    if not match:
        # Try URL-encoded
        print(f"    Warning: anchor '{story_name}' not found directly, searching...")
        return None

    start = match.start()

    # Find the next story header (next h2/h3 with an id)
    rest = html_content[start + len(match.group()):]
    next_header = re.search(r'<h[23][^>]*>\s*<span[^>]*id="[^"]*"', rest)
    if next_header:
        end = start + len(match.group()) + next_header.start()
        section = html_content[start:end]
    else:
        section = html_content[start:]

    # Parse text from section
    extractor = TextExtractor()
    extractor.feed(section)
    text = extractor.get_text().strip()

    # Clean up
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'^\s*\[编辑\]\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\[編輯\]', '', text)
    text = re.sub(r'^\s*$\n', '\n', text, flags=re.MULTILINE)

    return text.strip()


def main():
    # Group stories by volume
    volumes_needed = {}
    for vol, story, cat_name in STORIES:
        if vol not in volumes_needed:
            volumes_needed[vol] = []
        volumes_needed[vol].append((story, cat_name))

    all_stories = []

    for vol, stories in volumes_needed.items():
        print(f"Fetching volume {vol}...")
        html = fetch_volume(vol)
        time.sleep(1)

        for story_name, cat_name in stories:
            print(f"  Extracting {story_name} ({cat_name})...")
            text = extract_story(html, story_name)
            if text:
                all_stories.append((story_name, cat_name, text))
                print(f"    OK: {len(text)} chars")
            else:
                print(f"    FAILED to extract")

    # Write original.md
    output_dir = "obres/narrativa/pu-songling/liaozhai-zhiyi-seleccio-10-contes"

    with open(f"{output_dir}/original.md", "w", encoding="utf-8") as f:
        f.write("# 聊齋志異（選）\n\n")
        f.write("**蒲松齡**（1640–1715）\n\n")
        f.write("---\n\n")

        for story_zh, story_cat, text in all_stories:
            f.write(f"## {story_zh}\n\n")
            f.write(text)
            f.write("\n\n---\n\n")

    print(f"\nWritten {len(all_stories)} stories to {output_dir}/original.md")

    # Write metadata.yml
    total_chars = sum(len(t) for _, _, t in all_stories)
    story_list = "\n".join(f"  - \"{zh} ({cat})\"" for zh, cat, _ in all_stories)

    with open(f"{output_dir}/metadata.yml", "w", encoding="utf-8") as f:
        f.write(f"""obra:
  titol: "Liaozhai zhiyi (selecció: 10 contes fantàstics)"
  titol_original: "聊齋志異（選）"
  autor: "Pu Songling"
  autor_original: "蒲松齡"
  traductor: "Editorial Clàssica"
  any_original: "1679-1740"
  any_traduccio: 2026
  llengua_original: "xinès"
  descripcio: "Selecció de deu contes fantàstics de la col·lecció clàssica de relats sobrenaturals xinesos. Històries de fantasmes, esperits guineu, transformacions i mons paral·lels."
contes:
{story_list}
seccions: {len(all_stories)}
estadistiques:
  caracters_original: {total_chars}
  paraules_traduccio: 0
  notes: 0
  termes_glossari: 0
revisio:
  estat: "pendent"
  qualitat: 0
  data_revisio: ""
""")

    print(f"Written metadata.yml")


if __name__ == "__main__":
    main()
