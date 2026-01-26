#!/usr/bin/env python3
"""
Pipeline de traducció per a 'Sobre la quàdruple arrel del principi de raó suficient'
d'Arthur Schopenhauer.

Traducció de l'anglès al català amb sistema de logging complet.
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn, BarColumn

from agents.translator_agent import TranslatorAgent, TranslationRequest
from agents.reviewer_agent import ReviewerAgent, ReviewRequest
from utils.translation_logger import TranslationLogger, LogLevel

console = Console()

# Configuració
SOURCE_FILE = Path("data/originals/schopenhauer/fourfold_root_en.txt")
OUTPUT_DIR = Path("output/schopenhauer")
COST_LIMIT_EUR = 15.0  # Límit de seguretat


def clean_gutenberg_text(text: str) -> str:
    """Neteja el text de Project Gutenberg (elimina capçalera i peu)."""
    start_marker = "*** START OF THE PROJECT GUTENBERG EBOOK"
    end_marker = "*** END OF THE PROJECT GUTENBERG EBOOK"

    start_idx = text.find(start_marker)
    if start_idx != -1:
        start_idx = text.find("\n", start_idx) + 1

    end_idx = text.find(end_marker)
    if end_idx != -1:
        text = text[start_idx:end_idx].strip()
    elif start_idx != -1:
        text = text[start_idx:].strip()

    return text


def subdivide_large_section(title: str, content: str, max_chars: int = 10000) -> list[tuple[str, str]]:
    """Subdivideix una secció gran en parts més petites per paràgrafs."""
    if len(content) <= max_chars:
        return [(title, content)]

    paragraphs = content.split('\n\n')
    parts = []
    current_part = []
    current_size = 0
    part_num = 1

    for para in paragraphs:
        para_size = len(para) + 2

        if current_size + para_size > max_chars and current_part:
            part_content = '\n\n'.join(current_part)
            parts.append((f"{title} [Part {part_num}]", part_content))
            part_num += 1
            current_part = [para]
            current_size = para_size
        else:
            current_part.append(para)
            current_size += para_size

    if current_part:
        part_content = '\n\n'.join(current_part)
        if len(parts) > 0:
            parts.append((f"{title} [Part {part_num}]", part_content))
        else:
            parts.append((title, part_content))

    return parts


def split_by_sections(text: str, max_section_chars: int = 10000) -> list[tuple[str, str]]:
    """Divideix el text per seccions (§), subdividint les massa grans."""
    lines = text.split('\n')
    raw_sections = []
    current_section_title = "Introducció"
    current_section_content = []
    current_chapter = ""

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Detectar capítol
        if line.startswith('CHAPTER'):
            if current_section_content:
                content = '\n'.join(current_section_content).strip()
                if content:
                    raw_sections.append((f"{current_chapter} - {current_section_title}", content))
                current_section_content = []

            current_chapter = line
            current_section_title = "Introducció del capítol"
            i += 1
            continue

        # Detectar secció §
        if line.startswith('§'):
            if current_section_content:
                content = '\n'.join(current_section_content).strip()
                if content:
                    raw_sections.append((f"{current_chapter} - {current_section_title}", content))
                current_section_content = []

            current_section_title = line
            i += 1
            continue

        current_section_content.append(lines[i])
        i += 1

    # Guardar última secció
    if current_section_content:
        content = '\n'.join(current_section_content).strip()
        if content:
            raw_sections.append((f"{current_chapter} - {current_section_title}", content))

    # Subdividir seccions grans
    final_sections = []
    for title, content in raw_sections:
        subdivided = subdivide_large_section(title, content, max_section_chars)
        final_sections.extend(subdivided)

    return final_sections


def translate_chunk(
    translator: TranslatorAgent,
    reviewer: ReviewerAgent,
    chunk: str,
    chunk_num: int,
    logger: TranslationLogger,
    max_rounds: int = 2,
) -> tuple[str, int, float, float]:
    """Tradueix un chunk amb revisió i retorna (traducció, tokens, cost, qualitat)."""
    total_tokens = 0
    total_cost = 0.0
    quality_score = 0.0
    start_time = time.time()

    # Traducció inicial
    request = TranslationRequest(
        text=chunk,
        source_language="anglès",
        target_language="català",
        author="Arthur Schopenhauer",
        work_title="Sobre la quàdruple arrel del principi de raó suficient",
        preserve_formatting=True,
        literary_style="Filosòfic acadèmic, precís i rigorós"
    )

    response = translator.translate(request)
    translation = response.content
    tokens_in = response.usage.get("input_tokens", 0)
    tokens_out = response.usage.get("output_tokens", 0)
    total_tokens += tokens_in + tokens_out
    total_cost += response.cost_eur

    logger.log_api_call("Translator", tokens_in, tokens_out, response.cost_eur)

    # Parsejar JSON si és necessari
    try:
        result = json.loads(translation)
        translation = result.get("translation", result.get("traduccio", translation))
    except (json.JSONDecodeError, TypeError):
        pass

    logger.log_translation(chunk_num, translation)

    # Revisió iterativa
    for round_num in range(1, max_rounds + 1):
        review_request = ReviewRequest(
            original_text=chunk,
            translated_text=translation,
            source_language="anglès",
            target_language="català",
            author="Arthur Schopenhauer",
            work_title="Sobre la quàdruple arrel del principi de raó suficient"
        )

        review_response = reviewer.review(review_request)
        tokens_in = review_response.usage.get("input_tokens", 0)
        tokens_out = review_response.usage.get("output_tokens", 0)
        total_tokens += tokens_in + tokens_out
        total_cost += review_response.cost_eur

        logger.log_api_call("Reviewer", tokens_in, tokens_out, review_response.cost_eur)

        # Parsejar revisió
        try:
            review_result = json.loads(review_response.content)
            quality_score = review_result.get("score", review_result.get("puntuacio", 7.0))
            issues = len(review_result.get("issues", review_result.get("problemes", [])))

            logger.log_review(chunk_num, round_num, quality_score, issues)

            # Aplicar text revisat si existeix
            if review_result.get("text_revisat"):
                translation = review_result["text_revisat"]
            elif review_result.get("revised_text"):
                translation = review_result["revised_text"]

            # Si la qualitat és prou bona, sortir
            if quality_score >= 7.5:
                break

        except (json.JSONDecodeError, TypeError):
            quality_score = 7.0
            logger.warning("REVISIÓ", f"Chunk {chunk_num}: No s'ha pogut parsejar la revisió")
            break

    duration = time.time() - start_time
    return translation, total_tokens, total_cost, quality_score


def main():
    # Crear logger
    logger = TranslationLogger(
        log_dir=OUTPUT_DIR / "logs",
        project_name="Schopenhauer - Vierfache Wurzel",
        min_level=LogLevel.INFO,
    )

    # Verificar fitxer font
    if not SOURCE_FILE.exists():
        logger.critical("PIPELINE", f"No es troba el fitxer font: {SOURCE_FILE}")
        return 1

    # Llegir i netejar text
    text = SOURCE_FILE.read_text(encoding="utf-8")
    text = clean_gutenberg_text(text)
    logger.info("PIPELINE", f"Text original carregat: {len(text):,} caràcters")

    # Dividir per seccions
    sections = split_by_sections(text)
    logger.info("PIPELINE", f"Text dividit en {len(sections)} seccions")

    # Iniciar pipeline
    logger.start_pipeline(total_chunks=len(sections), source_file=str(SOURCE_FILE))

    # Crear directori de sortida
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Inicialitzar agents
    translator = TranslatorAgent()
    reviewer = ReviewerAgent()

    all_translations = []
    start_time = datetime.now()

    # Traduir cada secció
    for i, (section_title, section_content) in enumerate(sections, 1):
        logger.start_chunk(i, len(section_content))

        chunk_start = time.time()

        try:
            translation, tokens, cost, quality = translate_chunk(
                translator, reviewer, section_content, i, logger, max_rounds=2
            )

            # Verificar límit de cost
            if logger.stats["total_cost"] + cost > COST_LIMIT_EUR:
                logger.warning("COST", f"Límit de cost assolit (€{COST_LIMIT_EUR}). Aturant.")
                break

            # Afegir títol de secció a la traducció
            section_translation = f"\n{'='*60}\n{section_title}\n{'='*60}\n\n{translation}"
            all_translations.append(section_translation)

            duration = time.time() - chunk_start
            logger.complete_chunk(
                chunk_num=i,
                tokens=tokens,
                cost=cost,
                quality=quality,
                duration=duration,
            )

            # Desar progrés cada 10 seccions
            if i % 10 == 0:
                partial_file = OUTPUT_DIR / f"partial_{i:03d}.txt"
                partial_file.write_text('\n\n'.join(all_translations), encoding="utf-8")
                logger.info("BACKUP", f"Progrés desat a {partial_file}")

        except Exception as e:
            logger.error("CHUNK", f"Error a secció {i}: {str(e)}")
            all_translations.append(f"[ERROR: {e}]\n\n{section_title}\n\n{section_content}")

    # Fusionar traduccions
    logger.start_stage("fusió")

    header = """═══════════════════════════════════════════════════════════════════════════════
            SOBRE LA QUÀDRUPLE ARREL DEL PRINCIPI DE RAÓ SUFICIENT
                            Arthur Schopenhauer

                    Traducció al català des de l'anglès

                Editorial Clàssica - Sistema de Traducció amb IA
═══════════════════════════════════════════════════════════════════════════════

"""

    complete_translation = header + "\n\n".join(all_translations)

    # Desar traducció completa
    output_file = OUTPUT_DIR / "traduccio_completa.txt"
    output_file.write_text(complete_translation, encoding="utf-8")
    logger.success("OUTPUT", f"Traducció desada a {output_file}")

    # Desar també en format Markdown
    md_file = OUTPUT_DIR / "traduccio_revisada.md"
    md_content = f"""# Sobre la quàdruple arrel del principi de raó suficient

**Autor:** Arthur Schopenhauer
**Traducció:** Editorial Clàssica
**Data:** {datetime.now().strftime('%Y-%m-%d')}

---

{complete_translation}
"""
    md_file.write_text(md_content, encoding="utf-8")
    logger.success("OUTPUT", f"Versió Markdown desada a {md_file}")

    # Completar pipeline
    summary = logger.complete_pipeline()

    # Desar estadístiques
    stats_file = OUTPUT_DIR / "logs" / "translation_stats.json"
    stats = {
        "obra": "Sobre la quàdruple arrel del principi de raó suficient",
        "autor": "Arthur Schopenhauer",
        "data": datetime.now().isoformat(),
        "text_original_chars": len(text),
        "traduccio_chars": len(complete_translation),
        "seccions": len(sections),
        **summary
    }
    stats_file.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
