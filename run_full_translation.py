#!/usr/bin/env python3
"""Traducció extensa del Simposi amb monitorització completa."""

import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from pipeline import TranslationPipeline, PipelineConfig
from agents import AgentConfig, ChunkingStrategy
from utils.logger import VerbosityLevel, get_logger, reset_logger


def main():
    console = Console()

    console.print(Panel.fit(
        "[bold cyan]TRADUCCIÓ EXTENSA DEL SIMPOSI[/bold cyan]\n"
        "[dim]Amb sistema de logging i monitorització completa[/dim]",
        border_style="cyan",
    ))

    # Llegir text del Simposi
    greek_text_path = Path("data/originals/plato/symposium_greek.txt")
    if not greek_text_path.exists():
        console.print("[red]Error: No s'ha trobat el text grec[/red]")
        sys.exit(1)

    full_text = greek_text_path.read_text(encoding="utf-8")

    # Agafar una secció més gran (primers 10000 caràcters = ~5-6 chunks)
    sample_text = full_text[:10000]

    console.print(f"\n[green]Text a traduir:[/green] {len(sample_text):,} caràcters")
    console.print(f"[green]Tokens estimats:[/green] ~{len(sample_text) // 3:,}")
    console.print(f"[green]Chunks previstos:[/green] ~{len(sample_text) // 3 // 600 + 1}")

    # Estimació de cost
    estimated_cost = (len(sample_text) // 3) * 18 / 1_000_000 * 3 * 0.92
    console.print(f"[yellow]Cost estimat:[/yellow] €{estimated_cost:.2f} - €{estimated_cost * 1.5:.2f}")

    # Configurar logging en mode verbose
    reset_logger()
    logger = get_logger(
        verbosity=VerbosityLevel.VERBOSE,
        log_dir=Path("output/logs"),
        session_name="symposium_extended",
    )

    # Configuració del pipeline
    agent_config = AgentConfig(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        temperature=0.3,
    )

    pipeline_config = PipelineConfig(
        max_revision_rounds=1,
        min_quality_score=6.0,
        save_intermediate=True,
        output_dir=Path("output/symposium"),
        agent_config=agent_config,
        enable_chunking=True,
        max_tokens_per_chunk=800,
        min_tokens_per_chunk=400,
        overlap_tokens=50,
        chunking_strategy=ChunkingStrategy.PARAGRAPH,
        enable_cache=True,
        cache_dir=Path(".cache/symposium"),
        verbosity=VerbosityLevel.VERBOSE,
        use_dashboard=False,
        cost_limit_eur=3.0,
    )

    pipeline = TranslationPipeline(config=pipeline_config)

    console.print("\n[bold green]Iniciant traducció extensa...[/bold green]")
    console.print("=" * 70)

    try:
        result = pipeline.run(
            text=sample_text,
            source_language="grec",
            author="Plató",
            work_title="El Convit (Symposion)",
        )

        console.print("\n" + "=" * 70)
        pipeline.display_result(result)

        if result.final_translation:
            # Desar traducció
            output_path = Path("output/symposium/el_convit_parcial.txt")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(result.final_translation, encoding="utf-8")

            console.print(f"\n[bold green]Traducció desada a:[/bold green] {output_path}")

            # Mostrar detalls per chunk
            console.print("\n[bold cyan]Detall per chunk:[/bold cyan]")
            for i, cr in enumerate(result.chunk_results, 1):
                status = "✅" if cr.translated_text else "❌"
                chars = len(cr.original_text)
                trans_chars = len(cr.translated_text) if cr.translated_text else 0
                score = f"{cr.quality_score:.1f}" if cr.quality_score else "N/A"
                console.print(
                    f"  {status} Chunk {i}: {chars:,} chars → {trans_chars:,} chars traduïts, "
                    f"revisions: {cr.revision_rounds}, score: {score}"
                )

            # Resum final
            console.print("\n[bold]══════════════════════════════════════════════════[/bold]")
            console.print("[bold green]RESUM FINAL[/bold green]")
            console.print("[bold]══════════════════════════════════════════════════[/bold]")
            console.print(f"  📊 Chunks processats: {len(result.chunk_results)}")
            console.print(f"  📝 Tokens totals: {result.total_tokens:,}")
            console.print(f"  💰 Cost total: €{result.total_cost_eur:.4f}")
            console.print(f"  ⏱️  Temps total: {result.total_duration_seconds:.1f}s")
            console.print(f"  📈 Puntuació mitjana: {result.quality_score:.1f}/10" if result.quality_score else "  📈 Puntuació: N/A")
            console.print(f"  🔄 Revisions totals: {result.revision_rounds}")

            # Calcular velocitat
            words_translated = len(result.final_translation.split())
            words_per_second = words_translated / result.total_duration_seconds if result.total_duration_seconds > 0 else 0
            console.print(f"  ⚡ Velocitat: {words_per_second:.1f} paraules/segon")
            console.print("[bold]══════════════════════════════════════════════════[/bold]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Traducció interrompuda per l'usuari.[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
