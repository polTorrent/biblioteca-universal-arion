#!/usr/bin/env python3
"""Demo de traducció real amb un fragment curt per mostrar el sistema de logging."""

import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from pipeline import TranslationPipeline, PipelineConfig
from agents import AgentConfig, ChunkingStrategy
from utils.logger import VerbosityLevel, get_logger, reset_logger


# Text grec de mostra (primer paràgraf del Simposi)
SAMPLE_GREEK_TEXT = """
Ἀπολλόδωρος. Δοκῶ μοι περὶ ὧν πυνθάνεσθε οὐκ ἀμελέτητος εἶναι.
καὶ γὰρ ἐτύγχανον πρῴην εἰς ἄστυ οἴκοθεν ἀνιὼν Φαληρόθεν·
τῶν οὖν γνωρίμων τις ὄπισθεν κατιδών με πόρρωθεν ἐκάλεσε,
καὶ παίζων ἅμα τῇ κλήσει, Ὦ Φαληρεύς, ἔφη, οὗτος Ἀπολλόδωρος,
οὐ περιμενεῖς; κἀγὼ ἐπιστὰς περιέμεινα. καὶ ὅς, Ἀπολλόδωρε, ἔφη,
καὶ μὴν καὶ ἔναγχος ἐζήτουν σε βουλόμενος διαπυθέσθαι τὴν Ἀγάθωνος
συνουσίαν καὶ Σωκράτους καὶ Ἀλκιβιάδου καὶ τῶν ἄλλων τῶν τότε
ἐν τῷ συνδείπνῳ παραγενομένων, περὶ τῶν ἐρωτικῶν λόγων τίνες ἦσαν.
"""


def main():
    console = Console()

    console.print(Panel.fit(
        "[bold cyan]DEMO TRADUCCIÓ REAL[/bold cyan]\n"
        "[dim]Traducció d'un fragment del Simposi de Plató[/dim]",
        border_style="cyan",
    ))

    # Configurar logging en mode verbose
    reset_logger()
    logger = get_logger(
        verbosity=VerbosityLevel.VERBOSE,
        log_dir=Path("output/logs"),
        session_name="demo_real",
    )

    console.print(f"\n[green]Text original:[/green] {len(SAMPLE_GREEK_TEXT)} caràcters")
    console.print(f"[green]Tokens estimats:[/green] ~{len(SAMPLE_GREEK_TEXT) // 3}")

    # Configuració del pipeline (sense chunking per a un text curt)
    agent_config = AgentConfig(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        temperature=0.3,
    )

    pipeline_config = PipelineConfig(
        max_revision_rounds=1,  # Només 1 revisió per demo
        min_quality_score=6.0,
        save_intermediate=True,
        output_dir=Path("output/demo"),
        agent_config=agent_config,
        enable_chunking=False,  # Text massa curt
        enable_cache=True,
        cache_dir=Path(".cache/demo"),
        verbosity=VerbosityLevel.VERBOSE,
        use_dashboard=False,
        cost_limit_eur=1.0,  # Límit de cost per seguretat
    )

    # Crear i executar el pipeline
    pipeline = TranslationPipeline(config=pipeline_config)

    console.print("\n[bold green]Iniciant traducció...[/bold green]")
    console.print("=" * 60)

    try:
        result = pipeline.run(
            text=SAMPLE_GREEK_TEXT,
            source_language="grec",
            author="Plató",
            work_title="El Convit (Symposion) - Fragment inicial",
        )

        # Mostrar resultat
        console.print("\n" + "=" * 60)
        pipeline.display_result(result)

        if result.final_translation:
            console.print(Panel(
                result.final_translation,
                title="[bold green]Traducció completa[/bold green]",
                border_style="green",
            ))

            console.print(f"\n[bold]Estadístiques:[/bold]")
            console.print(f"  • Tokens processats: {result.total_tokens:,}")
            console.print(f"  • Cost total: €{result.total_cost_eur:.4f}")
            console.print(f"  • Temps total: {result.total_duration_seconds:.1f}s")
            console.print(f"  • Puntuació: {result.quality_score:.1f}/10" if result.quality_score else "  • Puntuació: N/A")

    except Exception as e:
        console.print(f"\n[red]Error durant la traducció: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
