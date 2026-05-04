#!/usr/bin/env python3
"""Script per continuar traducció de Lucreci des de l'últim punt."""
import subprocess
import time
import re
from pathlib import Path

VENICE_SCRIPT = Path.home() / ".hermes" / "skills/openclaw-imports" / "venice-ai" / "scripts" / "venice.py"
ORIGINAL_FILE = Path.home() / "biblioteca-universal-arion" / "obres/filosofia/lucreci/de-rerum-natura-llibre-i/original.md"
OUTPUT_FILE = Path.home() / "biblioteca-universal-arion" / "obres/filosofia/lucreci/de-rerum-natura-llibre-i/traduccio_nova.md"
MODEL = "claude-opus-4-7"
CHUNK_SIZE = 50

def get_verse_lines():
    """Llegeix l'original i retorna línies no buides sense metadades."""
    with open(ORIGINAL_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    verses = []
    for l in lines[7:]:  # Ignora capçalera
        l = l.strip()
        if l and not l.startswith('**'):
            verses.append(l)
    return verses

def get_last_translated_verse():
    """Extreu l'últim número de vers del fitxer de traducció."""
    if not OUTPUT_FILE.exists():
        return 0
    with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    # Busca patrons com "## Versos 305-354" o "## Invocació a Venus (versos 1-54)"
    matches = re.findall(r'##\s+(?:.+?\()?versos?\s+(\d+)(?:-\d+)?\)?', content, re.IGNORECASE)
    if matches:
        return int(matches[-1])
    # Si no troba, estima per nombre de línies
    lines = [l for l in content.split('\n') if l.strip() and not l.startswith('#')]
    return min(len(lines) // 2, len(get_verse_lines()))

def translate_chunk(verses_chunk, start_num):
    """Tradueix un chunk amb timeout de 120s."""
    latin_text = '\n'.join(verses_chunk)
    end_num = start_num + len(verses_chunk) - 1
    
    prompt = f"""Ets un traductor literari professional especialitzat en poesia llatina clàssica. Tradueix al català el següent fragment del De Rerum Natura de Lucreci (Llibre I, versos {start_num}-{end_num}).

IMPORTANT:
1. Tradueix EN PROSA POÈTICA CATALANA
2. Mantén el to filosòfic i argumentatiu
3. Conserva els noms propis
4. NO afegeixis comentaris ni explicacions, NOMÉS la traducció

TEXT LLATÍ:
{latin_text}"""

    try:
        result = subprocess.run([
            'python3', str(VENICE_SCRIPT),
            'chat', prompt,
            '--model', MODEL,
            '--max-tokens', '2000',
            '--temperature', '0.3'
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode != 0:
            print(f"ERROR: {result.stderr}")
            return None
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        print("TIMEOUT en chunk {start_num}")
        return None

def main():
    verses = get_verse_lines()
    total = len(verses)
    print(f"Total versos: {total}")
    
    start_from = get_last_translated_verse()
    print(f"Continuant des del vers {start_from + 1}")
    
    # Processa chunks
    for i in range(start_from, total, CHUNK_SIZE):
        chunk_verses = verses[i:i + CHUNK_SIZE]
        if len(chunk_verses) < 10:  # Si el chunk és molt petit, ignora
            break
            
        end_verse = min(i + CHUNK_SIZE, total)
        print(f"\n[{i+1}-{end_verse}/{total}] Traduint...")
        
        translation = translate_chunk(chunk_verses, i + 1)
        
        if translation:
            with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
                f.write(f"\n\n## Versos {i+1}-{end_verse}\n\n{translation}\n")
            print(f"✓ Versos {i+1}-{end_verse} traduïts")
            time.sleep(3)  # Pausa breu
        else:
            print(f"✗ Error, aturant...")
            break
        
        # Pausa llarga cada 5 chunks
        if (i // CHUNK_SIZE) % 5 == 4:
            print("Descansant 30s...")
            time.sleep(30)
    
    print("\nTraducció completada!")

if __name__ == "__main__":
    main()