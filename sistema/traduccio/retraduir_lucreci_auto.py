#!/usr/bin/env python3
"""Script automatitzat per retraduir Lucreci per chunks."""
import subprocess
import time
from pathlib import Path

VENICE_SCRIPT = Path.home() / ".hermes" / "skills/openclaw-imports" / "venice-ai" / "scripts" / "venice.py"
ORIGINAL_FILE = Path.home() / "biblioteca-universal-arion" / "obres/filosofia/lucreci/de-rerum-natura-llibre-i/original.md"
OUTPUT_FILE = Path.home() / "biblioteca-universal-arion" / "obres/filosofia/lucreci/de-rerum-natura-llibre-i/traduccio_nova.md"
MODEL = "claude-opus-4-7"
CHUNK_SIZE = 50  # versos per chunk

def get_verses_from_file():
    """Llegeix l'original i retorna versos (línies no buides)."""
    with open(ORIGINAL_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    # Filtra línies buides i metadades
    verses = [l.strip() for l in lines[7:] if l.strip() and not l.startswith('**')]  # Ignora capçalera
    return verses

def translate_chunk(verses_chunk, start_verse):
    """Tradueix un chunk de versos amb Venice."""
    latin_text = '\n'.join(verses_chunk)
    
    prompt = f"""Ets un traductor literari professional especialitzat en poesia llatina clàssica. Tradueix al català el següent fragment del De Rerum Natura de Lucreci (Llibre I, versos {start_verse}-{start_verse + len(verses_chunk) - 1}).

IMPORTANT:
1. Tradueix EN PROSA POÈTICA CATALANA, no en vers literal
2. Mantén el to filosòfic i argumentatiu de l'original
3. Conserva els noms propis (Venus, Memmi, Epicur, etc.)
4. Respecta el ritme i la musicalitat del llatí
5. NO afegeixis comentaris ni explicacions, NOMÉS la traducció

TEXT LLATÍ:
{latin_text}"""

    result = subprocess.run([
        'python3', str(VENICE_SCRIPT),
        'chat', prompt,
        '--model', MODEL,
        '--max-tokens', '2000',
        '--temperature', '0.3'
    ], capture_output=True, text=True, timeout=180)
    
    if result.returncode != 0:
        print(f"ERROR en chunk {start_verse}: {result.stderr}")
        return None
    
    return result.stdout.strip()

def main():
    verses = get_verses_from_file()
    total_verses = len(verses)
    print(f"Total versos a traduir: {total_verses}")
    
    # Llegeix traducció existent per veure on som
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            existing = f.read()
        # Compta quantes línies de traducció tenim (aproximadament)
        existing_lines = len([l for l in existing.split('\n') if l.strip() and not l.startswith('#')])
        # Estima versos traduïts (aprox 2 línies traducció per vers llatí)
        start_from = min(existing_lines // 2, total_verses)
        print(f"Continuant des del vers aproximadament {start_from}")
    else:
        # Escriu capçalera
        header = """# De Rerum Natura — Llibre I
*Lucreci*

Traduït del llatí per Biblioteca Arion

---

"""
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(header)
        start_from = 0
    
    # Processa chunks
    chunk_num = 0
    for i in range(start_from, total_verses, CHUNK_SIZE):
        chunk_verses = verses[i:i + CHUNK_SIZE]
        end_verse = min(i + CHUNK_SIZE, total_verses)
        
        print(f"\nTraduint versos {i+1}-{end_verse} de {total_verses}...")
        
        translation = translate_chunk(chunk_verses, i + 1)
        
        if translation:
            # Afegeix a la traducció
            with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
                f.write(f"\n\n## Versos {i+1}-{end_verse}\n\n{translation}\n")
            print(f"✓ Versos {i+1}-{end_verse} traduïts")
            
            # Pausa per evitar rate limits
            time.sleep(5)
        else:
            print(f"✗ Error en versos {i+1}-{end_verse}, aturant...")
            break
        
        chunk_num += 1
        
        # Comprova saldo cada 5 chunks
        if chunk_num % 5 == 0:
            print(f"Descansant 30 segons per evitar rate limits...")
            time.sleep(30)
    
    print(f"\nTraducció completada fins vers {i + len(chunk_verses)} de {total_verses}")

if __name__ == "__main__":
    main()