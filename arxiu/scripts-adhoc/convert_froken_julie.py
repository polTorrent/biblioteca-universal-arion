#!/usr/bin/env python3
"""Convert Fröken Julie wikitext from sv.wikisource to clean Markdown."""

import subprocess
import re

def main():
    # Fetch the raw wikitext
    result = subprocess.run(
        ['curl', '-sL', 'https://sv.wikisource.org/w/index.php?title=Fr%C3%B6ken_Julie&action=raw'],
        capture_output=True, text=True
    )
    raw = result.stdout

    # Remove Wikisource templates
    raw = re.sub(r'\{\{Titel\|[^}]*\}\}', '', raw)
    raw = re.sub(r'\{\{[^}]*\}\}', '', raw)

    # Convert wiki bold ''' to **
    raw = re.sub(r"'{3}([^']+)'{3}", r'**\1**', raw)
    # Convert wiki italic '' to *
    raw = re.sub(r"'{2}([^']+)'{2}", r'*\1*', raw)

    # Convert centered div character names to ### headings
    def convert_centered(m):
        content = m.group(1).strip()
        # Remove any remaining * from bold/italic conversion
        clean = content.replace('*', '')
        if clean == clean.upper() and clean.strip():
            # Character name (all caps) -> ### heading
            return '\n### ' + clean + '\n'
        else:
            # Stage direction (italic) -> *text*
            return '\n*' + clean + '*\n'

    raw = re.sub(
        r'<div style="text-align: center;">(.*?)</div>',
        convert_centered,
        raw
    )

    # Remove <br /> tags
    raw = raw.replace('<br />', '  ')
    raw = raw.replace('<br/>', '  ')

    # Clean up multiple blank lines
    raw = re.sub(r'\n{4,}', '\n\n\n', raw)

    # Build the final markdown
    header = (
        "# Fröken Julie\n\n"
        "**August Strindberg** (1888)\n\n"
        "Naturalistiskt sorgespel i en akt.\n\n"
        "Font: [Wikisource (sv)](https://sv.wikisource.org/wiki/Fröken_Julie)\n\n"
        "---\n\n"
    )

    output = header + raw.strip() + '\n'

    # Write to file
    path = (
        '/home/jo/biblioteca-universal-arion/obres/teatre/'
        'august-strindberg/froken-julie-la-senyoreta-julia/original.md'
    )
    with open(path, 'w', encoding='utf-8') as f:
        f.write(output)

    print(f'Written {len(output)} chars to original.md')
    print('First 300 chars of body:')
    body_start = output.find('---') + 4
    print(output[body_start:body_start+300])
    print('...')
    print('Last 200 chars:')
    print(output[-200:])


if __name__ == '__main__':
    main()
