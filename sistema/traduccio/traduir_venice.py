#!/usr/bin/env python3
"""Traducció simple amb Venice AI per obres de Biblioteca Arion.

Ús:
    python3 sistema/traduccio/traduir_venice.py --autor aristotil --obra peri-psykhes
    python3 sistema/traduccio/traduir_venice.py --ruta obres/filosofia/aristotil/peri-psykhes/

Aquest script és una alternativa al Pipeline V2 per quan Claude CLI no està disponible.
Utilitza Venice AI amb DIEM per a traduccions.

Models disponibles:
    - claude-opus-4-7: Filosofia/poesia (~3.5 DIEM)
    - claude-sonnet-4-6: Narrativa/assaig (~0.8 DIEM)
    - glm-5: Administratiu (~0.1 DIEM)
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# Constants
VENICE_SCRIPT = Path.home() / ".hermes" / "skills" / "openclaw-imports" / "venice-ai" / "scripts" / "venice.py"
DEFAULT_MODEL = "claude-sonnet-4-6"
CHUNK_SIZE = 500  # Caràcters per chunk (molt reduït per evitar timeouts en traduccions llargues)
MAX_RETRIES = 3
VENICE_TIMEOUT = 1200  # 20 minuts per models grans (Opus/DeepSeek)

# Model segons gènere
GENRE_MODELS = {
    "filosofia": "claude-opus-4-7",
    "poesia": "claude-opus-4-7",
    "teatre": "claude-opus-4-7",
    "narrativa": "claude-sonnet-4-6",
    "assaig": "claude-sonnet-4-6",
    "oriental": "claude-sonnet-4-6",
}


def run_venice(prompt: str, model: str, max_tokens: int = 4096) -> tuple[str, dict]:
    """Executa Venice i retorna la resposta i les metadades."""
    cmd = [
        "python3", str(VENICE_SCRIPT),
        "chat",
        "--model", model,
        "--max-tokens", str(max_tokens),
        "--temperature", "0.3",
        prompt
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=VENICE_TIMEOUT)
    
    if result.returncode != 0:
        raise RuntimeError(f"Venice error: {result.stderr}")
    
    return result.stdout.strip(), {}


def load_metadata(obra_dir: Path) -> dict:
    """Carrega metadata.yml."""
    meta_path = obra_dir / "metadata.yml"
    if not meta_path.exists():
        return {
            "titol": obra_dir.name.replace("-", " ").title(),
            "autor": obra_dir.parent.name.replace("-", " ").title(),
            "llengua": "llatí",
            "genere": "narrativa",
        }
    
    import yaml
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = yaml.safe_load(f) or {}
    
    obra = meta.get("obra", meta)
    return {
        "titol": obra.get("titol", obra.get("title", obra_dir.name)),
        "autor": obra.get("autor", obra.get("author", obra_dir.parent.name)),
        "llengua": obra.get("llengua_original", obra.get("source_language", "llatí")),
        "genere": obra.get("genere", obra.get("category", "narrativa")),
    }


def load_glossari(obra_dir: Path) -> str:
    """Carrega glossari.yml si existeix."""
    glossari_path = obra_dir / "glossari.yml"
    if not glossari_path.exists():
        return ""
    
    import yaml
    with open(glossari_path, "r", encoding="utf-8") as f:
        glossari = yaml.safe_load(f) or {}
    
    if not glossari:
        return ""
    
    termes = []
    for terme, traduccio in glossari.items():
        if isinstance(traduccio, dict):
            traduccio = traduccio.get("ca", traduccio.get("traduccio", ""))
        termes.append(f"  - {terme}: {traduccio}")
    
    return "\n".join(termes)


def load_memoria_contextual(obra_dir: Path) -> str:
    """Carrega la memòria contextual de la traducció anterior."""
    memoria_path = obra_dir / ".memoria_contextual.json"
    if not memoria_path.exists():
        return ""
    
    with open(memoria_path, "r", encoding="utf-8") as f:
        try:
            memoria = json.load(f)
            # Retornar els últims paràgrafs traduïts per context
            return memoria.get("ultim_context", "")
        except json.JSONDecodeError:
            return ""


def save_memoria_contextual(obra_dir: Path, context: str) -> None:
    """Guarda la memòria contextual per a la propera sessió."""
    memoria_path = obra_dir / ".memoria_contextual.json"
    memoria = {"ultim_context": context, "timestamp": time.time()}
    
    if memoria_path.exists():
        with open(memoria_path, "r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
                memoria["historial"] = existing.get("historial", [])
                memoria["historial"].append({"context": context, "timestamp": time.time()})
            except json.JSONDecodeError:
                pass
    
    with open(memoria_path, "w", encoding="utf-8") as f:
        json.dump(memoria, f, ensure_ascii=False, indent=2)


def chunk_text(text: str, max_chars: int = CHUNK_SIZE) -> list[str]:
    """Divideix el text en chunks respectant els paràgrafs."""
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 > max_chars and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = para
        else:
            current_chunk += "\n\n" + para if current_chunk else para
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


def build_translation_prompt(
    text: str,
    titol: str,
    autor: str,
    llengua: str,
    genere: str,
    glossari: str = "",
    context_anterior: str = "",
) -> str:
    """Construeix el prompt per a la traducció."""
    
    genre_instructions = {
        "filosofia": "Traducció filosòfica: claredat expositiva, precisió terminològica, respecte per l'argumentació. To didàctic i rigorós.",
        "poesia": "Traducció poètica: sentit > ritme > literalitat. Busca equivalents sonors. Permet llicències per musicalitat.",
        "teatre": "Traducció teatral: oralitat. Ha de sonar bé en veu alta. Frases que 'es puguin dir'. To viu i dinàmic.",
        "narrativa": "Traducció narrativa: preserva la VEU del narrador. Diàlegs naturals i creïbles. Ritme narratiu fidel a l'original.",
        "assaig": "Traducció d'assaig: claredat argumentativa. To personal de l'autor. Transicions lògiques fluides.",
        "oriental": "Traducció oriental: equilibri entre fidelitat i llegibilitat. Respecta les convencions del gènere oriental.",
    }
    
    instruccions = genre_instructions.get(genere, genre_instructions["narrativa"])
    
    prompt_parts = [
        f"[TRADUCCIÓ AL CATALÀ]",
        f"",
        f"Obra: {titol}",
        f"Autor: {autor}",
        f"Llengua original: {llengua}",
        f"Gènere: {genere}",
        f"",
        f"## Instruccions de traducció",
        f"",
        f"{instruccions}",
        f"",
    ]
    
    if glossari:
        prompt_parts.extend([
            f"## Glossari terminològic",
            f"",
            f"{glossari}",
            f"",
        ])
    
    if context_anterior:
        prompt_parts.extend([
            f"## Context anterior (últims paràgrafs traduïts)",
            f"",
            f"{context_anterior}",
            f"",
        ])
    
    prompt_parts.extend([
        f"## Text original ({llengua})",
        f"",
        f"```",
        f"{text}",
        f"```",
        f"",
        f"## Traducció al català",
        f"",
        f"Tradueix el text anterior al català seguint les instruccions. Només retorna la traducció, sense comentaris addicionals.",
    ])
    
    return "\n".join(prompt_parts)


def translate_chunk(
    chunk: str,
    metadata: dict,
    glossari: str,
    context_anterior: str,
    model: str,
) -> str:
    """Tradueix un chunk amb Venice."""
    prompt = build_translation_prompt(
        text=chunk,
        titol=metadata["titol"],
        autor=metadata["autor"],
        llengua=metadata["llengua"],
        genere=metadata["genere"],
        glossari=glossari,
        context_anterior=context_anterior,
    )
    
    for attempt in range(MAX_RETRIES):
        try:
            result, _ = run_venice(prompt, model, max_tokens=4096)
            return result
        except subprocess.TimeoutExpired:
            # Timeout: reduir chunk i reintentar
            if len(chunk) > 500:
                print(f"⏱️ Timeout ({VENICE_TIMEOUT}s), dividint chunk de {len(chunk)} chars...")
                half = len(chunk) // 2
                first_half = translate_chunk(chunk[:half], metadata, glossari, context_anterior, model)
                second_half = translate_chunk(chunk[half:], metadata, glossari, first_half[-500:], model)
                return first_half + "\n\n" + second_half
            else:
                raise RuntimeError(f"Timeout en chunk petit ({len(chunk)} chars) després de {VENICE_TIMEOUT}s")
        except RuntimeError as e:
            if "rate limit" in str(e).lower():
                print(f"Rate limit, esperant 30s...")
                time.sleep(30)
            elif "unicode" in str(e).lower() or "encoding" in str(e).lower():
                print(f"Error d'encoding, dividint chunk...")
                # Dividir chunk encara més
                half = len(chunk) // 2
                first_half = translate_chunk(chunk[:half], metadata, glossari, context_anterior, model)
                second_half = translate_chunk(chunk[half:], metadata, glossari, first_half[-500:], model)
                return first_half + "\n\n" + second_half
            elif attempt < MAX_RETRIES - 1:
                print(f"Error (intento {attempt+1}/{MAX_RETRIES}): {e}")
                time.sleep(10)
            else:
                raise


def main():
    parser = argparse.ArgumentParser(description="Traducció amb Venice AI")
    parser.add_argument("--autor", help="Nom de l'autor (ex: aristotil)")
    parser.add_argument("--obra", help="Nom de l'obra (ex: peri-psykhes)")
    parser.add_argument("--ruta", help="Ruta directa a l'obra (ex: obres/filosofia/aristotil/peri-psykhes)")
    parser.add_argument("--model", help="Model a utilitzar (ex: claude-opus-4-7)")
    parser.add_argument("--start", type=int, default=0, help="Chunk d'inici (per reprendre)")
    parser.add_argument("--continuar", action="store_true", help="Continuar des de l'últim chunk")
    args = parser.parse_args()
    
    # Determinar ruta de l'obra
    if args.ruta:
        obra_dir = Path(args.ruta).resolve()
    elif args.autor and args.obra:
        # Buscar l'obra a obres/*/
        for categoria in ["filosofia", "narrativa", "poesia", "teatre", "assaig", "oriental"]:
            candidate = Path(f"obres/{categoria}/{args.autor}/{args.obra}")
            if candidate.exists():
                obra_dir = candidate.resolve()
                break
        else:
            print(f"❌ No s'ha trobat l'obra: {args.autor}/{args.obra}")
            sys.exit(1)
    else:
        print("❌ Cal especificar --autor i --obra o --ruta")
        sys.exit(1)
    
    if not obra_dir.exists():
        print(f"❌ No existeix: {obra_dir}")
        sys.exit(1)
    
    # Carregar metadata
    metadata = load_metadata(obra_dir)
    print(f"📖 {metadata['titol']} de {metadata['autor']}")
    print(f"🌐 {metadata['llengua']} → català | Gènere: {metadata['genere']}")
    
    # Seleccionar model
    model = args.model or GENRE_MODELS.get(metadata["genere"], DEFAULT_MODEL)
    print(f"🤖 Model: {model}")
    
    # Carregar original
    original_path = obra_dir / "original.md"
    if not original_path.exists():
        print(f"❌ No existeix original.md")
        sys.exit(1)
    
    with open(original_path, "r", encoding="utf-8") as f:
        text_original = f.read()
    
    # Netejar metadata del font
    for footer in ["*Text de domini públic", "*Traducció de domini públic"]:
        if footer in text_original:
            text_original = text_original.split(footer)[0].strip()
    
    # Trobar inici del contingut
    match = re.search(r'^(##\s+|[一二三四五六七八九十]+\s*$|[IVXLCDM]+\s*$)', text_original, re.MULTILINE)
    if match:
        text_narratiu = text_original[match.start():]
    else:
        text_narratiu = text_original
    
    # Treure footer final
    footer_hrule = '---\n\n*'
    last_pos = text_narratiu.rfind(footer_hrule)
    if last_pos > 0 and (len(text_narratiu) - last_pos) < 200:
        text_narratiu = text_narratiu[:last_pos].strip()
    
    print(f"📝 Text: {len(text_narratiu)} caràcters")
    
    # Dividir en chunks
    chunks = chunk_text(text_narratiu)
    print(f"📦 Chunks: {len(chunks)}")
    
    # Carregar glossari
    glossari = load_glossari(obra_dir)
    
    # Carregar traducció existent si --continuar
    traduccio_path = obra_dir / "traduccio.md"
    traduccio_exist = ""
    start_chunk = args.start
    
    if args.continuar and traduccio_path.exists():
        with open(traduccio_path, "r", encoding="utf-8") as f:
            traduccio_exist = f.read()
        # Trobar l'últim chunk traduït
        # Assumir que cada chunk és un paràgraf aproximat
        chars_exist = len(traduccio_exist)
        start_chunk = chars_exist // CHUNK_SIZE
        print(f"↩️ Continuant des del chunk {start_chunk}")
    
    # Context anterior
    context_anterior = ""
    if traduccio_exist:
        # Últims 500 caràcters com a context
        context_anterior = traduccio_exist[-500:] if len(traduccio_exist) > 500 else traduccio_exist
    context_anterior = load_memoria_contextual(obra_dir) or context_anterior
    
    # Traduir chunks
    traduccions = []
    errors = []
    
    for i, chunk in enumerate(chunks[start_chunk:], start=start_chunk):
        print(f"\n[{i+1}/{len(chunks)}] Traduint {len(chunk)} caràcters...")
        
        try:
            traduccio = translate_chunk(
                chunk=chunk,
                metadata=metadata,
                glossari=glossari,
                context_anterior=context_anterior,
                model=model,
            )
            traduccions.append(traduccio)
            context_anterior = traduccio[-500:] if len(traduccio) > 500 else traduccio
            
            # Guardar memòria cada5 chunks
            if (i+ 1) % 5 == 0:
                save_memoria_contextual(obra_dir, context_anterior)
            
            print(f"✅ Chunk {i+1} completat")
            
        except Exception as e:
            print(f"❌ Error en chunk {i+1}: {e}")
            errors.append((i, str(e)))
            # Guardar el que tenim i continuar
            traduccions.append(f"[ERROR: {e}]")
    
    # Combinar traduccions
    traduccio_final = "\n\n".join(traduccions)
    
    # Si continuem, afegir a l'existent
    if traduccio_exist:
        # Treure el footer del final
        if "*Traducció de domini públic*" in traduccio_exist:
            traduccio_exist = traduccio_exist.split("*Traducció de domini públic*")[0].strip()
        traduccio_final = traduccio_exist + "\n\n" + traduccio_final
    
    # Aplicar format final
    output = f"""# {metadata['titol']}
*{metadata['autor']}*

Traduït del {metadata['llengua']} per Biblioteca Arion

---

{traduccio_final}

---

*Traducció de domini públic.*
"""
    
    # Guardar
    with open(traduccio_path, "w", encoding="utf-8") as f:
        f.write(output)
    
    print(f"\n✅ Traducció guardada a: {traduccio_path}")
    
    # Guardar memòria final
    save_memoria_contextual(obra_dir, context_anterior)
    
    # Eliminar .needs_fix o .fixing
    for f in [".needs_fix", ".fixing"]:
        p = obra_dir / f
        if p.exists():
            p.unlink()
            print(f"🗑️ Eliminat {f}")
    
    # Report d'errors
    if errors:
        print(f"\n⚠️ Errors en {len(errors)} chunks:")
        for idx, err in errors:
            print(f"   Chunk {idx}: {err}")
    
    print(f"\n📊 Estadístiques:")
    print(f"   Chunks traduïts: {len(traduccions)}")
    print(f"   Errors: {len(errors)}")
    print(f"   Model utilitzat: {model}")


if __name__ == "__main__":
    main()