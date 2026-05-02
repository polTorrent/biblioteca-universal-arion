#!/usr/bin/env python3
"""Descarrega URLs externes per a Biblioteca Arion.

Ús:
    python3 sistema/traduccio/fetch_url.py --url "https://..." --output "obres/filosofia/aristotil/peri-psykhes/original.md"
    python3 sistema/traduccio/fetch_url.py --url "https://..." --output "-" --stdout | ... 
    
Tipus de fonts suportades:
    - Project Gutenberg (text pla)
    - Wikisource (HTML extret del div.mw-parser-output)
    - Internet Archive (text pla o HTML)
    - Perseus (text pla)
    - URLs genèriques (text pla o HTML extret)
"""

import argparse
import html
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


def fetch_url(url: str, timeout: int = 60) -> str:
    """Descarrega una URL i retorna el contingut."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (BibliotecaArion/1.0; +https://github.com/polTorrent/biblioteca-universal-arion)',
        'Accept': 'text/html,application/xhtml+xml,text/plain,*/*',
        'Accept-Language': 'en,ca,es,fr,de,la',
    }
    req = urllib.request.Request(url, headers=headers)
    
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        content = resp.read().decode('utf-8', errors='replace')
        return content
    except urllib.error.HTTPError as e:
        print(f"❌ Error HTTP {e.code}: {e.reason}", file=sys.stderr)
        return ""
    except urllib.error.URLError as e:
        print(f"❌ Error de connexió: {e.reason}", file=sys.stderr)
        return ""
    except TimeoutError:
        print(f"❌ Timeout després de {timeout}s", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return ""


def extract_text_from_html(html_content: str, source_type: str = "auto") -> str:
    """Extrau text net d'HTML segons el tipus de font."""
    
    if source_type == "wikisource" or "wikisource" in html_content.lower():
        # Extreure div.mw-parser-output
        m = re.search(r'class="mw-parser-output"[^>]*>(.*?)(?:<div class="printfooter|<!--\s*\nNewPP)', html_content, re.DOTALL)
        if m:
            content = m.group(1)
        else:content = html_content
        
        # Netejar
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
        content = re.sub(r'<table[^>]*>.*?</table>', '', content, flags=re.DOTALL)
        content = re.sub(r'<div class="ws-noexport"[^>]*>.*?</div>', '', content, flags=re.DOTALL)
        
    elif source_type == "gutenberg" or "gutenberg" in html_content.lower():
        # Project Gutenberg: extreure contingut principal
        m = re.search(r'<div[^>]*class="[^"]*text[^"]*"[^>]*>(.*?)</div>', html_content, re.DOTALL)
        if m:
            content = m.group(1)
        else:
            # Intentar extreure entre pre o text pla
            m = re.search(r'<pre[^>]*>(.*?)</pre>', html_content, re.DOTALL)
            content = m.group(1) if m else html_content
    
    elif source_type == "perseus" or "perseus" in html_content.lower():
        # Perseus Digital Library
        m = re.search(r'<div[^>]*class="[^"]*text[^"]*"[^>]*>(.*?)</div>', html_content, re.DOTALL)
        content = m.group(1) if m else html_content
    
    else:
        # Auto-detecció o genèric
        # Intentar extreure el cos principal
        m = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL | re.IGNORECASE)
        content = m.group(1) if m else html_content
    
    # Conversió comú d'HTML a text
    # Headers
    content = re.sub(r'<h1[^>]*>(.*?)</h1>', r'\n# \1\n', content, flags=re.DOTALL)
    content = re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n## \1\n', content, flags=re.DOTALL)
    content = re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n### \1\n', content, flags=re.DOTALL)
    
    # Paràgrafs i salts de línia
    content = re.sub(r'<p[^>]*>', '\n\n', content)
    content = re.sub(r'</p>', '\n', content)
    content = re.sub(r'<br\s*/?>', '\n', content)
    
    # Referències i notes
    content = re.sub(r'<sup[^>]*>.*?</sup>', '', content, flags=re.DOTALL)
    content = re.sub(r'<a[^>]*>(.*?)</a>', r'\1', content, flags=re.DOTALL)
    
    # Eliminar tags restants
    content = re.sub(r'<[^>]+>', '', content)
    
    # Decodificar entitats HTML
    content = html.unescape(content)
    
    # Netejar línies buides excessives
    lines = [line.strip() for line in content.split('\n')]
    lines = [line for line in lines if line or (lines.index(line) > 0 and lines[lines.index(line)-1])]
    content = '\n'.join(lines)
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    return content.strip()


def detect_source_type(url: str) -> str:
    """Detecta el tipus de font des de la URL."""
    url_lower = url.lower()
    
    if "gutenberg" in url_lower:
        return "gutenberg"
    elif "wikisource" in url_lower:
        return "wikisource"
    elif "perseus" in url_lower or "tufts.edu" in url_lower:
        return "perseus"
    elif "archive.org" in url_lower:
        return "archive"
    else:
        return "generic"


def main():
    parser = argparse.ArgumentParser(description="Descarrega URLs per a Biblioteca Arion")
    parser.add_argument("--url", required=True, help="URL a descarregar")
    parser.add_argument("--output", required=True, help="Fitxer de sortida (o '-' per stdout)")
    parser.add_argument("--type", choices=["auto", "text", "html"], default="auto",
                        help="Tipus de contingut (auto=text+HTML, text=pla, html=sense processar)")
    parser.add_argument("--source", choices=["auto", "gutenberg", "wikisource", "perseus", "archive", "generic"],
                        default="auto", help="Tipus de font (auto-detecció per defecte)")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout en segons")
    parser.add_argument("--header", action="append", help="Headers HTTP addicionals (format: 'Key: Value')")
    
    args = parser.parse_args()
    
    # Descarregar
    print(f"📥 Descarregant: {args.url}", file=sys.stderr)
    content = fetch_url(args.url, timeout=args.timeout)
    
    if not content:
        print("❌ Error: Contingut buit", file=sys.stderr)
        sys.exit(1)
    
    print(f"✓ Descarregats {len(content)} caràcters", file=sys.stderr)
    
    # Detectar tipus de font
    source_type = args.source
    if source_type == "auto":
        source_type = detect_source_type(args.url)
    
    # Processar segons tipus
    if args.type == "text" or (args.type == "auto" and ("<html" in content.lower() or "<div" in content.lower())):
        print(f"📄 Extreient text de HTML ({source_type})", file=sys.stderr)
        content = extract_text_from_html(content, source_type)
    # Si type == "html", deixar sense processar
    
    # Afegir capçalera amb metadades
    header = f"""# Original descarregat
**Font:** {args.url}
**Descarregat:** {Path(__file__).stem}

---

"""
    content = header + content
    
    # Sortida
    if args.output == "-":
        print(content)
    else:
        outpath = Path(args.output)
        outpath.parent.mkdir(parents=True, exist_ok=True)
        outpath.write_text(content, encoding="utf-8")
        print(f"✓ Desat a: {outpath}", file=sys.stderr)
        print(f"✓ Total: {len(content)} caràcters, {len(content.splitlines())} línies", file=sys.stderr)


if __name__ == "__main__":
    main()