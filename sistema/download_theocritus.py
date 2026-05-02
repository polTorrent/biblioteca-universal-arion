#!/usr/bin/env python3
"""
Descarrega el text grec dels Idil·lis de Teòcrit des de Perseus.
"""
import urllib.request
import urllib.parse
import re
from html.parser import HTMLParser

class GreekTextExtractor(HTMLParser):
    """Extreu el text grec de l'HTML de Perseus."""
    
    def __init__(self):
        super().__init__()
        self.greek_text = []
        self.in_greek = False
        self.current_text = []
    
    def handle_starttag(self, tag, attrs):
        if tag == 'span':
            for attr, value in attrs:
                if attr == 'class' and 'greek' in value:
                    self.in_greek = True
                    break
    
    def handle_endtag(self, tag):
        if tag == 'span' and self.in_greek:
            self.in_greek = False
            if self.current_text:
                self.greek_text.append(' '.join(self.current_text))
                self.current_text = []
    
    def handle_data(self, data):
        if self.in_greek:
            text = data.strip()
            if text:
                self.current_text.append(text)

def download_idylls():
    """Descarrega els Idil·lis de Teòcrit."""
    
    # Idil·lis que necessitem (I, II, III, VI, VII, XI, XV)
    idylls = [1, 2, 3, 6, 7, 11, 15]
    
    base_url = 'https://www.perseus.tufts.edu/hopper/text'
    
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
        print(f"Descarregant Idil·li {i}...")
        
        # URL per a cada idil·li
        params = {
            'doc': f'Perseus:text:1999.01.0228:text=Id.:poem={i}'
        }
        url = base_url + '?' + urllib.parse.urlencode(params)
        
        try:
            # Descarregar la pàgina
            with urllib.request.urlopen(url) as response:
                html = response.read().decode('utf-8', errors='ignore')
            
            # Extreure el text grec
            parser = GreekTextExtractor()
            parser.feed(html)
            
            if parser.greek_text:
                full_text += f"## {idyll_titles[i]}\n\n"
                full_text += '\n\n'.join(parser.greek_text)
                full_text += "\n\n---\n\n"
                print(f"  ✅ Idil·li {i}: {len(parser.greek_text)} línies gregues")
            else:
                print(f"  ⚠️ Idil·li {i}: No s'ha trobat text grec")
                full_text += f"## {idyll_titles[i]}\n\n"
                full_text += "[Text no disponible]\n\n---\n\n"
        
        except Exception as e:
            print(f"  ❌ Error descarregant Idil·li {i}: {e}")
            full_text += f"## {idyll_titles[i]}\n\n"
            full_text += f"[Error: {e}]\n\n---\n\n"
    
    # Guardar el text complet
    output_file = '/home/jo/biblioteca-universal-arion/obres/poesia/teocrit/idillis/original.md'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(full_text)
    
    print(f"\n✅ Text grec guardat a: {output_file}")
    print(f"Total: {len(idylls)} idil·lis descarregats")

if __name__ == '__main__':
    download_idylls()