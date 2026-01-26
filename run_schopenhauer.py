#!/usr/bin/env python3
"""
Pipeline de traducció per a 'Sobre la quàdruple arrel del principi de raó suficient'
d'Arthur Schopenhauer.

Utilitza el pipeline complet amb els 5 agents:
- ChunkerAgent: Divideix el text en chunks
- GlossaristaAgent: Genera glossari terminològic
- TranslatorAgent: Tradueix
- ReviewerAgent: Revisa (N rondes)
- CorrectorAgent: Corregeix IEC
"""

import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel

from pipeline.translation_pipeline import PipelineConfig, TranslationPipeline
from utils.logger import VerbosityLevel

console = Console()

# Configuració
SOURCE_FILE = Path("data/originals/schopenhauer/fourfold_root_en.txt")
OUTPUT_DIR = Path("output/schopenhauer")


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


def main():
    console.print(Panel.fit(
        "[bold cyan]PIPELINE DE TRADUCCIÓ COMPLET[/bold cyan]\n"
        "[yellow]Sobre la quàdruple arrel del principi de raó suficient[/yellow]\n"
        "Arthur Schopenhauer\n\n"
        "[dim]5 agents: Chunker → Glossarista → Traductor → Revisor → Corrector[/dim]",
        title="🏛️ Editorial Clàssica"
    ))

    # Verificar fitxer font
    if not SOURCE_FILE.exists():
        console.print(f"[red]Error: No es troba {SOURCE_FILE}[/red]")
        return 1

    # Llegir i netejar text
    text = SOURCE_FILE.read_text(encoding="utf-8")
    text = clean_gutenberg_text(text)
    console.print(f"\n[bold]Text original:[/bold] {len(text):,} caràcters (~{len(text)//3:,} tokens)")

    # Configuració optimitzada per filosofia
    config = PipelineConfig(
        # Agents actius
        enable_chunking=True,
        enable_glossary=True,        # Important per terminologia filosòfica
        enable_correction=True,      # Correcció IEC
        correction_level="estricte", # Màxima qualitat

        # Paràmetres de chunking
        max_tokens_per_chunk=2500,   # Chunks mitjans per mantenir context
        min_tokens_per_chunk=500,
        overlap_tokens=150,          # Solapament per coherència

        # Revisió
        max_revision_rounds=2,       # 2 rondes de revisió
        min_quality_score=7.5,       # Llindar alt

        # Costos i control
        cost_limit_eur=15.0,         # Límit de seguretat

        # Sortida
        output_dir=OUTPUT_DIR,
        save_intermediate=True,      # Guardar progrés

        # Visualització
        verbosity=VerbosityLevel.NORMAL,
        use_dashboard=False,

        # Translation logger
        use_translation_logger=True,
        project_name="Schopenhauer - Vierfache Wurzel",
    )

    # Crear directori de sortida
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Executar pipeline
    console.print("\n[bold]Iniciant pipeline...[/bold]\n")

    pipeline = TranslationPipeline(config)

    result = pipeline.run(
        text=text,
        source_language="anglès",
        author="Arthur Schopenhauer",
        work_title="Sobre la quàdruple arrel del principi de raó suficient",
    )

    # Guardar traducció completa
    header = """═══════════════════════════════════════════════════════════════════════════════
            SOBRE LA QUÀDRUPLE ARREL DEL PRINCIPI DE RAÓ SUFICIENT
                            Arthur Schopenhauer

                    Traducció al català des de l'anglès

                Editorial Clàssica - Sistema de Traducció amb IA
═══════════════════════════════════════════════════════════════════════════════

"""
    complete_translation = header + result.final_translation

    output_file = OUTPUT_DIR / "traduccio_completa.txt"
    output_file.write_text(complete_translation, encoding="utf-8")

    # Guardar glossari si existeix
    if result.accumulated_context.glossary:
        glossary_file = OUTPUT_DIR / "glossari.json"
        glossary_data = {
            k: {
                "original": v.term_original,
                "traduit": v.term_translated,
                "context": v.context,
            }
            for k, v in result.accumulated_context.glossary.items()
        }
        glossary_file.write_text(
            json.dumps(glossary_data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        console.print(f"[green]✓[/green] Glossari desat: {glossary_file}")

    # Resum final
    console.print(Panel.fit(
        f"[bold green]✅ TRADUCCIÓ COMPLETADA[/bold green]\n\n"
        f"📄 Fitxer: {output_file}\n"
        f"📊 Mida: {len(complete_translation):,} caràcters\n"
        f"⏱️ Temps: {result.total_duration_seconds/60:.1f} minuts\n"
        f"🔤 Tokens: {result.total_tokens:,}\n"
        f"💰 Cost: €{result.total_cost_eur:.4f}\n"
        f"⭐ Qualitat: {result.quality_score:.1f}/10\n"
        f"📦 Chunks: {len(result.chunk_results)}",
        border_style="green"
    ))

    # Desar estadístiques
    stats = {
        "obra": "Sobre la quàdruple arrel del principi de raó suficient",
        "autor": "Arthur Schopenhauer",
        "data": datetime.now().isoformat(),
        "text_original_chars": len(text),
        "traduccio_chars": len(complete_translation),
        "chunks": len(result.chunk_results),
        "temps_segons": result.total_duration_seconds,
        "tokens_totals": result.total_tokens,
        "cost_eur": result.total_cost_eur,
        "qualitat_mitjana": result.quality_score,
        "rondes_revisio": result.revision_rounds,
    }

    stats_file = OUTPUT_DIR / "logs" / "translation_stats.json"
    stats_file.parent.mkdir(parents=True, exist_ok=True)
    stats_file.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
