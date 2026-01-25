#!/usr/bin/env python3
"""
Pipeline de traducció per a 'Sobre la quàdruple arrel del principi de raó suficient'
d'Arthur Schopenhauer.

Traducció de l'anglès al català usant els agents directament.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn, BarColumn

from agents.translator_agent import TranslatorAgent, TranslationRequest
from agents.reviewer_agent import ReviewerAgent, ReviewRequest

console = Console()

# Configuració
SOURCE_FILE = Path("data/originals/schopenhauer/fourfold_root_only.txt")
OUTPUT_DIR = Path("output/schopenhauer")


def subdivide_large_section(title: str, content: str, max_chars: int = 10000) -> list[tuple[str, str]]:
    """Subdivideix una secció gran en parts més petites per paràgrafs.

    Args:
        title: Títol de la secció
        content: Contingut de la secció
        max_chars: Màxim de caràcters per part

    Returns:
        Llista de tuples (títol_part, contingut_part)
    """
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
            # Guardar part actual
            part_content = '\n\n'.join(current_part)
            parts.append((f"{title} [Part {part_num}]", part_content))
            part_num += 1
            current_part = [para]
            current_size = para_size
        else:
            current_part.append(para)
            current_size += para_size

    # Última part
    if current_part:
        part_content = '\n\n'.join(current_part)
        if len(parts) > 0:
            parts.append((f"{title} [Part {part_num}]", part_content))
        else:
            parts.append((title, part_content))

    return parts


def split_by_sections(text: str, max_section_chars: int = 10000) -> list[tuple[str, str]]:
    """Divideix el text per seccions (§), subdividint les massa grans.

    Args:
        text: Text complet
        max_section_chars: Màxim de caràcters per secció

    Returns:
        Llista de tuples (títol_secció, contingut)
    """
    # Primer, detectem els capítols i les seves seccions
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
            # Guardar secció anterior si n'hi ha
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
            # Guardar secció anterior
            if current_section_content:
                content = '\n'.join(current_section_content).strip()
                if content:
                    raw_sections.append((f"{current_chapter} - {current_section_title}", content))
                current_section_content = []

            current_section_title = line
            i += 1
            continue

        # Afegir línia al contingut actual
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


def translate_chunk(translator: TranslatorAgent, reviewer: ReviewerAgent,
                    chunk: str, chunk_num: int) -> tuple[str, int, float]:
    """Tradueix un chunk i retorna (traducció, tokens, cost)."""
    total_tokens = 0
    total_cost = 0.0

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
    total_tokens += response.usage.get("input_tokens", 0) + response.usage.get("output_tokens", 0)
    total_cost += response.cost_eur

    # Intentar parsejar JSON si és necessari
    try:
        result = json.loads(translation)
        translation = result.get("translation", result.get("traduccio", translation))
    except (json.JSONDecodeError, TypeError):
        pass

    # Revisió
    review_request = ReviewRequest(
        original_text=chunk,
        translated_text=translation,
        source_language="anglès",
        target_language="català",
        author="Arthur Schopenhauer",
        work_title="Sobre la quàdruple arrel del principi de raó suficient"
    )

    review_response = reviewer.review(review_request)
    total_tokens += review_response.usage.get("input_tokens", 0) + review_response.usage.get("output_tokens", 0)
    total_cost += review_response.cost_eur

    # Parsejar revisió
    try:
        review_result = json.loads(review_response.content)
        if review_result.get("text_revisat"):
            translation = review_result["text_revisat"]
        elif review_result.get("revised_text"):
            translation = review_result["revised_text"]
    except (json.JSONDecodeError, TypeError):
        pass

    return translation, total_tokens, total_cost


def main():
    console.print(Panel.fit(
        "[bold cyan]PIPELINE DE TRADUCCIÓ[/bold cyan]\n"
        "[yellow]Sobre la quàdruple arrel del principi de raó suficient[/yellow]\n"
        "Arthur Schopenhauer\n\n"
        "[dim]Traducció anglès → català[/dim]",
        title="Editorial Clàssica"
    ))

    # Verificar fitxer font
    if not SOURCE_FILE.exists():
        console.print(f"[red]Error: No es troba {SOURCE_FILE}[/red]")
        return 1

    # Llegir text
    text = SOURCE_FILE.read_text(encoding="utf-8")
    console.print(f"\n[bold]Text original:[/bold] {len(text):,} caràcters")

    # Dividir per seccions (§)
    sections = split_by_sections(text)
    console.print(f"[bold]Seccions a traduir:[/bold] {len(sections)}")

    # Mostrar estructura
    console.print("\n[dim]Estructura detectada:[/dim]")
    for i, (title, content) in enumerate(sections[:10], 1):
        console.print(f"  [dim]{i}. {title[:60]}... ({len(content):,} chars)[/dim]")
    if len(sections) > 10:
        console.print(f"  [dim]... i {len(sections) - 10} seccions més[/dim]")
    console.print()

    # Crear directori de sortida
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "logs").mkdir(exist_ok=True)

    # Inicialitzar agents
    translator = TranslatorAgent()
    reviewer = ReviewerAgent()

    all_translations = []
    total_tokens = 0
    total_cost = 0.0
    start_time = datetime.now()

    # Traduir cada chunk
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:

        task = progress.add_task("Traduint...", total=len(sections))

        for i, (section_title, section_content) in enumerate(sections, 1):
            progress.update(task, description=f"Traduint § {i}/{len(sections)}...")

            try:
                translation, tokens, cost = translate_chunk(
                    translator, reviewer, section_content, i
                )

                # Afegir títol de secció a la traducció
                section_translation = f"\n{'='*60}\n{section_title}\n{'='*60}\n\n{translation}"
                all_translations.append(section_translation)
                total_tokens += tokens
                total_cost += cost

                # Log cada 5 seccions
                if i % 5 == 0:
                    console.print(f"  [green]✓[/green] Seccions {i}/{len(sections)} - Tokens: {total_tokens:,}, Cost: €{total_cost:.4f}")

            except Exception as e:
                console.print(f"  [red]✗[/red] Error secció {i}: {e}")
                all_translations.append(f"[ERROR: {e}]\n\n{section_title}\n\n{section_content}")

            progress.update(task, advance=1)

            # Desar progrés cada 10 seccions
            if i % 10 == 0:
                partial_file = OUTPUT_DIR / f"partial_{i:03d}.txt"
                partial_file.write_text('\n\n'.join(all_translations), encoding="utf-8")

    # Fusionar traduccions
    console.print("\n[bold]Fusionant traduccions...[/bold]")

    header = """═══════════════════════════════════════════════════════════════════════════════
            SOBRE LA QUÀDRUPLE ARREL DEL PRINCIPI DE RAÓ SUFICIENT
                            Arthur Schopenhauer

                    Traducció al català des de l'anglès

                Editorial Clàssica - Sistema de Traducció amb IA
═══════════════════════════════════════════════════════════════════════════════

"""

    complete_translation = header + "\n\n".join(all_translations)

    # Desar traducció completa
    output_file = OUTPUT_DIR / "SCHOPENHAUER_RAO_SUFICIENT_COMPLET.txt"
    output_file.write_text(complete_translation, encoding="utf-8")

    duration = (datetime.now() - start_time).total_seconds()

    # Resum final
    console.print(Panel.fit(
        f"[bold green]TRADUCCIÓ COMPLETADA[/bold green]\n\n"
        f"Fitxer: {output_file}\n"
        f"Mida: {len(complete_translation):,} caràcters\n"
        f"Temps: {duration/60:.1f} minuts\n"
        f"Tokens: {total_tokens:,}\n"
        f"Cost: €{total_cost:.4f}",
        border_style="green"
    ))

    # Desar estadístiques
    stats = {
        "obra": "Sobre la quàdruple arrel del principi de raó suficient",
        "autor": "Arthur Schopenhauer",
        "data": datetime.now().isoformat(),
        "text_original_chars": len(text),
        "traduccio_chars": len(complete_translation),
        "seccions": len(sections),
        "temps_segons": duration,
        "tokens_totals": total_tokens,
        "cost_eur": total_cost
    }

    stats_file = OUTPUT_DIR / "logs" / "translation_stats.json"
    stats_file.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
