#!/usr/bin/env python3
"""Demo de traducció amb chunking per mostrar progress bars."""

import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from pipeline import TranslationPipeline, PipelineConfig
from agents import AgentConfig, ChunkingStrategy
from utils.logger import VerbosityLevel, get_logger, reset_logger


def main():
    console = Console()

    console.print(Panel.fit(
        "[bold cyan]DEMO TRADUCCIÓ AMB CHUNKING[/bold cyan]\n"
        "[dim]Traducció de múltiples paràgrafs del Simposi[/dim]",
        border_style="cyan",
    ))

    # Llegir més text del Simposi
    greek_text_path = Path("data/originals/plato/symposium_greek.txt")
    if not greek_text_path.exists():
        console.print("[red]Error: No s'ha trobat el text grec[/red]")
        sys.exit(1)

    full_text = greek_text_path.read_text(encoding="utf-8")

    # Agafar els primers 4000 caràcters (aprox 3 chunks)
    sample_text = full_text[:4000]

    # Configurar logging en mode verbose
    reset_logger()
    logger = get_logger(
        verbosity=VerbosityLevel.VERBOSE,
        log_dir=Path("output/logs"),
        session_name="chunked_demo",
    )

    console.print(f"\n[green]Text original:[/green] {len(sample_text):,} caràcters")
    console.print(f"[green]Tokens estimats:[/green] ~{len(sample_text) // 3:,}")

    # Configuració del pipeline amb chunking
    agent_config = AgentConfig(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        temperature=0.3,
    )

    pipeline_config = PipelineConfig(
        max_revision_rounds=1,
        min_quality_score=6.0,
        save_intermediate=True,
        output_dir=Path("output/chunked_demo"),
        agent_config=agent_config,
        # Chunking config - forçar chunks petits per la demo
        enable_chunking=True,
        max_tokens_per_chunk=500,  # Chunks petits per veure'n més
        min_tokens_per_chunk=200,
        overlap_tokens=50,
        chunking_strategy=ChunkingStrategy.AUTO,
        # Cache i visualització
        enable_cache=True,
        cache_dir=Path(".cache/chunked_demo"),
        verbosity=VerbosityLevel.VERBOSE,
        use_dashboard=False,
        cost_limit_eur=2.0,  # Límit de seguretat
    )

    # Crear i executar el pipeline
    pipeline = TranslationPipeline(config=pipeline_config)

    console.print("\n[bold green]Iniciant traducció amb chunking...[/bold green]")
    console.print("=" * 60)

    try:
        result = pipeline.run(
            text=sample_text,
            source_language="grec",
            author="Plató",
            work_title="El Convit (Symposion)",
        )

        # Mostrar resultat
        console.print("\n" + "=" * 60)
        pipeline.display_result(result)

        if result.final_translation:
            # Mostrar detalls per chunk
            console.print("\n[bold]Detall per chunk:[/bold]")
            for i, cr in enumerate(result.chunk_results, 1):
                status = "✅" if cr.translated_text else "❌"
                score = f"{cr.quality_score:.1f}" if cr.quality_score else "N/A"
                console.print(f"  {status} Chunk {i}: {len(cr.original_text)} chars, score: {score}")

            console.print(f"\n[bold green]Traducció completada amb èxit![/bold green]")
            console.print(f"  • Chunks processats: {len(result.chunk_results)}")
            console.print(f"  • Tokens totals: {result.total_tokens:,}")
            console.print(f"  • Cost total: €{result.total_cost_eur:.4f}")
            console.print(f"  • Temps total: {result.total_duration_seconds:.1f}s")

    except Exception as e:
        console.print(f"\n[red]Error durant la traducció: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
