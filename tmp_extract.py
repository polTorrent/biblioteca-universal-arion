#!/usr/bin/env python3
"""Extract specific stories from Liaozhai Zhiyi using Wikisource API wikitext."""
import json
import re
import os
import sys


def load_wikitext(filepath):
    """Load wikitext from API JSON response."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('parse', {}).get('wikitext', {}).get('*', '')


def extract_story_from_wikitext(wikitext, story_title):
    """Extract a story by title from wikitext content.

    Stories are delimited by == Title == headings.
    """
    # Find the heading for this story
    # Pattern: == story_title ==
    heading_pattern = r'==\s*' + re.escape(story_title) + r'\s*=='
    match = re.search(heading_pattern, wikitext)
    if not match:
        return None

    # Get text after this heading until next == heading ==
    start = match.end()
    next_heading = re.search(r'\n==\s*[^=]', wikitext[start:])
    if next_heading:
        story_wiki = wikitext[start:start + next_heading.start()]
    else:
        story_wiki = wikitext[start:]

    # Clean up wikitext markup
    text = story_wiki

    # Remove <ref>...</ref> tags and their content
    text = re.sub(r'<ref[^/]*>.*?</ref>', '', text, flags=re.DOTALL)
    text = re.sub(r'<ref[^/]*/>', '', text)

    # Remove <u>...</u> tags but keep content
    text = re.sub(r'</?u>', '', text)

    # Remove other HTML-like tags
    text = re.sub(r'<[^>]+>', '', text)

    # Remove [[ ]] wiki links - keep display text
    # [[target|display]] -> display
    text = re.sub(r'\[\[[^\]]*\|([^\]]*)\]\]', r'\1', text)
    # [[target]] -> target
    text = re.sub(r'\[\[([^\]]*)\]\]', r'\1', text)

    # Remove {{ }} templates
    text = re.sub(r'\{\{[^}]*\}\}', '', text)

    # Remove bold/italic markup
    text = re.sub(r"'{2,5}", '', text)

    # Clean up whitespace but preserve paragraph structure
    # Chinese text uses \u3000 (ideographic space) for indentation
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped:
            cleaned_lines.append(stripped)

    result = '\n\n'.join(cleaned_lines)
    return result.strip()


def main():
    base = "/home/jo/biblioteca-universal-arion"

    # Volume files (API JSON)
    vol_files = {
        1: f"{base}/.tmp_api_vol1.json",
        2: f"{base}/.tmp_api_vol2.json",
        4: f"{base}/.tmp_api_vol4.json",
        7: f"{base}/.tmp_api_vol7.json",
        10: f"{base}/.tmp_api_vol10.json",
    }

    # Stories in order with their volumes and English subtitles
    stories = [
        ("聶小倩", 2, "Nie Xiaoqian"),
        ("畫皮", 1, "The Painted Skin"),
        ("嬰寧", 2, "Yingning, the Laughing Girl"),
        ("促織", 4, "The Cricket"),
        ("席方平", 10, "Xi Fangping"),
        ("阿寶", 2, "A Bao"),
        ("青鳳", 1, "Qingfeng, the Green Phoenix"),
        ("小翠", 7, "Xiao Cui"),
        ("狐嫁女", 1, "The Fox Marries Off Her Daughter"),
        ("勞山道士", 1, "The Taoist of Laoshan"),
    ]

    # Load all volumes
    volumes = {}
    for v, fp in vol_files.items():
        try:
            volumes[v] = load_wikitext(fp)
            print(f"Loaded volume {v}: {len(volumes[v])} chars", file=sys.stderr)
        except Exception as e:
            print(f"ERROR loading volume {v}: {e}", file=sys.stderr)

    if sys.argv[1:] and sys.argv[1] == 'headings':
        for v, wt in sorted(volumes.items()):
            headings = re.findall(r'==\s*([^=\n]+?)\s*==', wt)
            # Filter to only h2 (not h3 etc)
            h2s = []
            for h in headings:
                if not h.startswith('='):
                    h2s.append(h)
            print(f"Volume {v}: {h2s[:20]}...")
        return

    # Extract each story
    results = {}
    for title, vol, subtitle in stories:
        if vol not in volumes:
            print(f"NOT FOUND (no volume): {title}", file=sys.stderr)
            continue
        text = extract_story_from_wikitext(volumes[vol], title)
        if text and len(text) > 50:
            results[title] = text
            print(f"FOUND: {title} in vol {vol}, {len(text)} chars", file=sys.stderr)
        else:
            print(f"NOT FOUND: {title} in vol {vol}", file=sys.stderr)

    if sys.argv[1:] and sys.argv[1] == 'preview':
        for title, vol, subtitle in stories:
            print(f"\n===== {title} ({subtitle}) =====")
            if title in results:
                print(results[title][:400])
                print(f"... [{len(results[title])} chars total]")
            else:
                print("NOT FOUND")
        return

    # Build the output file
    output_parts = []
    output_parts.append("# \u804a\u9f4b\u8a8c\u7570 (Liaozhai Zhiyi) \u2014 Selecci\u00f3 de 10 contes fant\u00e0stics\n")
    output_parts.append("**Autor**: \u84b2\u677e\u9f61 (Pu Songling, 1640-1715)")
    output_parts.append("**Font**: Wikisource (zh.wikisource.org)")
    output_parts.append("**Llengua**: xin\u00e8s cl\u00e0ssic (\u6587\u8a00\u6587)\n")
    output_parts.append("---\n")

    for i, (title, vol, subtitle) in enumerate(stories, 1):
        output_parts.append(f"## {i}. {title} ({subtitle})\n")
        if title in results:
            output_parts.append(results[title])
        else:
            output_parts.append("[Text no disponible]")
        output_parts.append("\n---\n")

    # Write the file
    outdir = f"{base}/obres/narrativa/pu-songling/liaozhai-zhiyi-seleccio-10-contes"
    os.makedirs(outdir, exist_ok=True)
    outpath = f"{outdir}/original.md"
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_parts))
    print(f"\nWritten to {outpath}", file=sys.stderr)
    print(f"Total stories found: {len(results)}/10", file=sys.stderr)


if __name__ == '__main__':
    main()
