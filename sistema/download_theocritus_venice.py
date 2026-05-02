#!/usr/bin/env python3
"""
Descarrega el text grec dels Idil·lis de Teòcrit utilitzant Venice AI per extreure'l.
"""
import subprocess
import json
import re

def extract_greek_with_venice(url, idyll_num):
    """Utilitza Venice AI per extreure el text grec d'una URL."""
    
    prompt = f"""
    Extreu el text grec del Idil·li {idyll_num} de Teòcrit d'aquesta URL: {url}
    
    Necessito NOMÉS el text grec original, sense comentaris ni traduccions.
    
    Format de sortida:
    - Text grec complet del poema
    - Format: una línia per línia del poema
    - Sense numeració, sense títols, només el text grec
    
    Si hi ha capçaleres o comentaris en grec, exclou-los. Només vull el text del poema.
    """
    
    cmd = [
        'python3',
        '/home/jo/.openclaw/workspace/skills/venice-ai/scripts/venice.py',
        'chat', prompt,
        '--model', 'deepseek-v3.2',
        '--max-tokens', '3000',
        '--web-scrape'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"Error Venice: {result.stderr}")
            return None
    except subprocess.TimeoutExpired:
        print(f"Timeout descarregant Idil·li {idyll_num}")
        return None

def download_idylls():
    """Descarrega els Idil·lis de Teòcrit."""
    
    # Idil·lis que necessitem (I, II, III, VI, VII, XI, XV)
    idylls = [1, 2, 3, 6, 7, 11, 15]
    
    # URLs base
    base_url = 'https://www.perseus.tufts.edu/hopper/text?doc=Perseus%3Atext%3A1999.01.0228%3Atext%3DId.%3Apoem%3D'
    
    full_text = "# Εἰδύλλια (Idil·lis) — Selecció\n\n"
    full_text += "**Autor:** Θεόκριτος (Teòcrit)\n"
    full_text += "**Llengua:** grec antic (dialecte dòric literari)\n"
    full_text += "**Font:** Perseus Digital Library\n"
    full_text += "**Edició:** A.S.F. Gow, *Theocritus* (Cambridge, 1952)\n\n"
    full_text += "---\n\n"
    
    idyll_titles = {
        1: "Idil·li I — Θύρσις ἢ ᾠδή (Tirsis o el Cant)",
        2: "Idil·li II — Φαρμακεύτριαι (Les Encantadores)",
        3: "Idil·li III — Κῶμος (El Comus)",
        6: "Idil·li VI — Βουκολιασταί (Els Bucòlics)",
        7: "Idil·li VII — Θαλύσια (Les Talíssies)",
        11: "Idil·li XI — Κύκλωψ (El Ciclop)",
        15: "Idil·li XV — Συρακόσιαι ἢ Ἀδωνιάζουσαι (Les Siracusanes o Les Adònies)"
    }
    
    for i in idylls:
        url = f"{base_url}{i}"
        print(f"Processant Idil·li {i}...")
        
        greek_text = extract_greek_with_venice(url, i)
        
        if greek_text:
            full_text += f"## {idyll_titles[i]}\n\n"
            full_text += greek_text
            full_text += "\n\n---\n\n"
            print(f"  ✅ Idil·li {i}: descarregat")
        else:
            print(f"  ⚠️ Idil·li {i}: error en l'extracció")
            full_text += f"## {idyll_titles[i]}\n\n"
            full_text += "[Text no disponible]\n\n---\n\n"
    
    # Guardar el text complet
    output_file = '/home/jo/biblioteca-universal-arion/obres/poesia/teocrit/idillis/original.md'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(full_text)
    
    print(f"\n✅ Text grec guardat a: {output_file}")

if __name__ == '__main__':
    download_idylls()