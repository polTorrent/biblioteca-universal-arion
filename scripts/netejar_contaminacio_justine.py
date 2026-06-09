#!/usr/bin/env python3
"""
Neteja quirúrgica de contaminació de prompt a Justine.
- Elimina chunks buits o que només contenen ```json
- Elimina chunks amb text en anglès de prompt (thinking del model)
- Elimina blocs JSON incrustats (metadades d'auto-revisió)
- Reconstrueix traduccio.md a partir de chunks nets
- Preserva ordre i integritat del text
"""
import json, re, sys
from pathlib import Path

PROJECT = Path.home() / "biblioteca-universal-arion"
OBRA = PROJECT / "obres" / "narrativa" / "sade" / "justine"
CHUNKS_FILE = OBRA / ".chunks_traduïts.json"
TRADUCCIO_FILE = OBRA / "traduccio.md"

# Patrons de contaminació
PROMPT_CONTAMINATION = re.compile(
    r"(The user wants me to (translate|analyze|carefully translate).*"  
    r"|Let me (carefully|analyze|translate).*"
    r"|I need to translate.*"
    r"|I will translate.*"
    r"|Here is the translation.*"
    r"|Now I(?:'ll|\s+will) translate.*"
    r"|Translating the passage.*"
    r"|The passage argues that.*"
    r"|Continuing the translation.*"
    r"|I am (?:now\s+)?translating.*"
    r"|I am seeing how.*"
    r"|Now I am considering.*"
    r"|I am now seeing.*"
    r"|Now I am viewing.*"
    r"|Now considering.*"
    r"|Ara estic veient.*"
    r"|Ara estic considerant.*"
    r"|Continuant amb la traducció.*)",
    re.IGNORECASE
)

# Patrons de JSON incrustat
JSON_BLOCK = re.compile(r"```json\s*\n[^`]*```", re.DOTALL)
EMPTY_JSON_BLOCK = re.compile(r"```json\s*\n?\s*```", re.DOTALL)

def is_contaminated(chunk_text: str) -> bool:
    """Determina si un chunk està contaminat."""
    if not chunk_text or not chunk_text.strip():
        return True
    stripped = chunk_text.strip()
    # Buit o només whitespace
    if len(stripped) == 0:
        return True
    # Només blocs JSON buits
    if stripped == "```json\n```" or stripped == "```json\n\n```":
        return True
    # Conté text de prompt en anglès
    if PROMPT_CONTAMINATION.search(stripped):
        return True
    return False

def clean_chunk(chunk_text: str) -> str | None:
    """Neteja un chunk individual. Retorna None si s'ha de descartar."""
    if not chunk_text:
        return None
    
    # Si està completament contaminat, descartar
    if is_contaminated(chunk_text):
        return None
    
    # Netejar blocs JSON incrustats dins text vàlid
    cleaned = JSON_BLOCK.sub("", chunk_text)
    cleaned = EMPTY_JSON_BLOCK.sub("", cleaned)
    
    # Netejar línies de thinking residual en anglès
    lines = cleaned.splitlines()
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        # Descartar línies que són purament thinking del model
        if (stripped.startswith("The user wants me to") or
            stripped.startswith("Let me ") or
            stripped.startswith("I need to translate") or
            stripped.startswith("I will translate") or
            stripped.startswith("Here is the translation") or
            stripped.startswith("Now I'll") or
            stripped.startswith("Now I will") or
            stripped.startswith("Translating the") or
            stripped.startswith("The passage argues") or
            stripped.startswith("Continuing the") or
            stripped.startswith("I am translating") or
            stripped.startswith("I am now translating") or
            stripped.startswith("Now I am") or
            stripped.startswith("I am seeing") or
            stripped.startswith("Now considering") or
            stripped.startswith("Ara estic veient") or
            stripped.startswith("Ara estic considerant") or
            stripped.startswith("Continuant amb la traducció") or
            stripped.startswith("The user wants")):
            continue
        # Descartar línies que són numeració de llista de raonament
        if re.match(r"^\d+\.[\s\t].*(passage|translate|translation|arguments|philosophical|virtue|vice|Zadig|Jesrad|Nature|Providence)", stripped, re.I):
            continue
        clean_lines.append(line)
    
    result = "\n".join(clean_lines).strip()
    return result if result else None

def main():
    if not CHUNKS_FILE.exists():
        print(f"ERROR: No trobo {CHUNKS_FILE}", file=sys.stderr)
        sys.exit(1)
    
    # Llegir chunks
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    
    print(f"Chunks originals: {len(chunks)}")
    
    # Netejar
    clean_chunks = {}
    removed = 0
    for key, text in chunks.items():
        cleaned = clean_chunk(text)
        if cleaned is None:
            removed += 1
            print(f"  DESCARTAT: {key}")
        else:
            clean_chunks[key] = cleaned
    
    print(f"Chunks nets: {len(clean_chunks)} (descartats: {removed})")
    
    # Sobreescriure .chunks_traduïts.json amb chunks nets
    with open(CHUNKS_FILE, "w", encoding="utf-8") as f:
        json.dump(clean_chunks, f, ensure_ascii=False, indent=2)
    print(f"Escrit: {CHUNKS_FILE}")
    
    # Reconstruir traduccio.md
    # Ordenar per número de chunk
    def chunk_sort_key(item):
        key = item[0]
        try:
            num = int(key.replace("chunk_", ""))
            return num
        except:
            return 99999
    
    sorted_chunks = sorted(clean_chunks.items(), key=chunk_sort_key)
    
    # Unir amb separador lògic
    parts = []
    for key, text in sorted_chunks:
        parts.append(text)
    
    # Reconstruir: afegir separadors entre chunks si cal
    # Buscar si hi ha separadors tipus "---" o línies en blanc
    assembled = "\n\n".join(parts)
    
    # Netejar dobles salts de línia excessius
    assembled = re.sub(r"\n{4,}", "\n\n\n", assembled)
    
    with open(TRADUCCIO_FILE, "w", encoding="utf-8") as f:
        f.write(assembled)
    print(f"Escrit: {TRADUCCIO_FILE}")
    
    # Verificació final
    with open(TRADUCCIO_FILE, "r", encoding="utf-8") as f:
        final_text = f.read()
    
    remaining_contam = len(PROMPT_CONTAMINATION.findall(final_text))
    remaining_json = len(JSON_BLOCK.findall(final_text))
    
    print(f"\nVerificació:")
    print(f"  - Contaminació de prompt restant: {remaining_contam}")
    print(f"  - Blocs JSON restants: {remaining_json}")
    print(f"  - Línies totals: {len(final_text.splitlines())}")
    print(f"  - Caràcters totals: {len(final_text)}")
    
    if remaining_contam == 0 and remaining_json == 0:
        print("\n✓ Neteja completada amb èxit.")
        return 0
    else:
        print(f"\n⚠ Queden {remaining_contam + remaining_json} contaminacions.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
