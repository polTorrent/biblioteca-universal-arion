#!/usr/bin/env python3
"""
Reformateja obres de teatre per a mòbil
Separa parlaments, destaca noms de personatge, millora llegibilitat
"""
import re
import sys
from pathlib import Path


def format_teatre(obra_path: str) -> int:
    """Reformateja una obra de teatre."""

    with open(obra_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    in_dialogue = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Detectar noms de personatge (format: _Nom._ o Nom.)
        char_match = re.match(r'^_([A-ZÀ-Ú][a-zà-úïü]*)_?\.?\s*(.*)', stripped)
        if not char_match:
            char_match = re.match(r'^([A-ZÀ-Ú]{2,}[a-zà-úïü]*)\.?\s+(.*)', stripped)
        
        if char_match:
            # Afegir línia en buit abans del parlament
            if new_lines and new_lines[-1].strip():
                new_lines.append('\n')
            
            nom = char_match.group(1)
            resta = char_match.group(2) if len(char_match.groups()) > 1 else ''
            
            # Format: **NOM:** text
            new_lines.append(f'**{nom.upper()}:** {resta}\n')
            in_dialogue = True
        elif stripped.startswith('_') and stripped.endswith('_') and len(stripped) > 2:
            # Didascàlia en cursiva
            if new_lines and new_lines[-1].strip():
                new_lines.append('\n')
            new_lines.append(f'*{stripped[1:-1]}*\n')
            in_dialogue = False
        elif stripped.startswith('#'):
            # Títols
            if new_lines and new_lines[-1].strip():
                new_lines.append('\n')
            new_lines.append(line)
            in_dialogue = False
        elif stripped == '---':
            new_lines.append('\n---\n\n')
            in_dialogue = False
        elif stripped:
            # Text normal
            new_lines.append(f'{stripped}\n')
        else:
            # Línia buida
            if new_lines and new_lines[-1].strip():
                new_lines.append('\n')
    
    # Escriure el fitxer reformatejat
    with open(obra_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    return len(new_lines)

if __name__ == '__main__':
    obra = sys.argv[1] if len(sys.argv) > 1 else 'traduccio.md'
    if not Path(obra).is_file():
        print(f"Error: no existeix el fitxer '{obra}'", file=sys.stderr)
        sys.exit(1)
    lines = format_teatre(obra)
    print(f"Reformatejat: {lines} linies")