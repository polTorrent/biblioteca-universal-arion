#!/usr/bin/env python3
"""Demostració del sistema de logging i dashboard sense API."""

import time
import random
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from utils.logger import VerbosityLevel, get_logger, reset_logger
from utils.dashboard import Dashboard


def simulate_agent_work(logger, agent_name: str, duration: float = 1.0):
    """Simula el treball d'un agent amb logging."""
    logger.log_start(agent_name, "Processant text...")
    time.sleep(duration)

    # Simular tokens i cost
    input_tokens = random.randint(500, 1500)
    output_tokens = random.randint(300, 1000)
    cost = (input_tokens * 3 + output_tokens * 15) / 1_000_000 * 0.92

    logger.log_complete(
        agent_name,
        duration_seconds=duration,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_eur=cost,
    )
    return input_tokens, output_tokens, cost


def demo_logging_modes():
    """Demostra els diferents modes de logging."""
    console = Console()

    console.print(Panel.fit(
        "[bold cyan]DEMOSTRACIÓ SISTEMA DE LOGGING[/bold cyan]",
        border_style="cyan",
    ))

    # Mode VERBOSE
    console.print("\n[bold yellow]═══ MODE VERBOSE ═══[/bold yellow]\n")
    reset_logger()
    logger = get_logger(
        verbosity=VerbosityLevel.VERBOSE,
        log_dir=Path("output/logs"),
        session_name="demo_verbose",
    )

    logger.log_session_start("El Convit", "Plató", estimated_cost=5.0)

    # Simular agents
    simulate_agent_work(logger, "Chunker", 0.5)

    for i in range(3):
        logger.log_progress("Pipeline", i + 1, 3, "Processant chunk")
        simulate_agent_work(logger, "Traductor", 0.8)
        simulate_agent_work(logger, "Revisor", 0.6)

    logger.log_warning("Revisor", "Qualitat del chunk 2 inferior al mínim (6.5/10)")
    logger.log_session_end()

    console.print("\n[dim]Fitxer de log creat a: output/logs/[/dim]")


def demo_dashboard():
    """Demostra el dashboard interactiu."""
    console = Console()

    console.print("\n[bold yellow]═══ DEMOSTRACIÓ DASHBOARD ═══[/bold yellow]\n")
    console.print("[dim]Mostrant dashboard durant 8 segons...[/dim]\n")

    dashboard = Dashboard(
        work_title="El Convit (Symposion)",
        author="Plató",
        source_language="grec",
        total_chunks=5,
    )

    with dashboard:
        # Simular processament
        stages = ["Seccionant", "Traduint", "Revisant", "Refinant", "Fusionant"]

        for stage_idx, stage in enumerate(stages[:3]):
            dashboard.set_stage(stage, stage_idx + 1)

            for chunk in range(1, 6):
                dashboard.set_chunk(chunk, 5)
                dashboard.set_active_agent(
                    "Traductor" if stage == "Traduint" else "Revisor",
                    f"Processant chunk {chunk}/5",
                    progress=chunk * 20,
                    total=100,
                )

                # Simular treball
                time.sleep(0.3)

                # Actualitzar estadístiques
                tokens = random.randint(800, 1200)
                cost = tokens * 0.000018 * 0.92
                dashboard.add_tokens(tokens)
                dashboard.add_cost(cost)
                dashboard.add_words(random.randint(150, 300))

                # Estimar temps restant
                remaining = (5 - chunk) * 0.5 + (2 - stage_idx) * 2.5
                dashboard.set_estimated_remaining(remaining)

                if chunk == 3 and stage == "Revisant":
                    dashboard.add_warning("Qualitat baixa al chunk 3")

        dashboard.set_stage("Completat", 5)
        time.sleep(1)

    console.print("\n[bold green]Dashboard tancat.[/bold green]")


def demo_progress_output():
    """Mostra l'output típic del pipeline en mode verbose."""
    console = Console()

    console.print("\n[bold yellow]═══ EXEMPLE OUTPUT PIPELINE ═══[/bold yellow]\n")

    # Simular output del pipeline
    output_lines = """
[14:23:45] 🚀 [bold green]Iniciant traducció:[/bold green] El Convit (Symposion)
[14:23:45] 📚 [bold]Autor:[/bold] Plató
[14:23:45] 💰 [bold]Cost estimat:[/bold] €5.50

[14:23:45] 🚀 [bold blue][Pipeline][/bold blue] Text: 12,450 paraules, ~4,150 tokens

[14:23:46] ✂️  [bold cyan][Chunker][/bold cyan] Processant...
[14:23:47] ✅ [bold green][Chunker][/bold green] Completat (1.2s, 0 tokens, €0.0000)

[14:23:47] 🚀 [bold blue][Pipeline][/bold blue] Fase 1: Seccionant el text...
[14:23:47] ✂️  [bold blue][Chunker][/bold blue] Text dividit en 15 chunks (paragraph)

[14:23:47] 🚀 [bold blue][Pipeline][/bold blue] Fase 2: Processant chunks...

[14:23:47] ⏳ [bold cyan][Pipeline][/bold cyan] Processant chunk (1/15, 7%)
[14:23:48] 🌍 [bold cyan][Traductor][/bold cyan] Processant...
[14:23:52] ✅ [bold green][Traductor][/bold green] Completat (3.8s, 2,450 tokens, €0.0412)

[14:23:52] 📝 [bold cyan][Revisor][/bold cyan] Processant...
[14:23:55] ✅ [bold green][Revisor][/bold green] Completat (2.9s, 3,120 tokens, €0.0524)

[14:23:55] ⏳ [bold cyan][Pipeline][/bold cyan] Processant chunk (2/15, 13%)
[14:23:56] 🌍 [bold cyan][Traductor][/bold cyan] Processant...
[14:24:00] ✅ [bold green][Traductor][/bold green] Completat (4.1s, 2,680 tokens, €0.0450)

[14:24:00] 📝 [bold cyan][Revisor][/bold cyan] Processant...
[14:24:03] ✅ [bold green][Revisor][/bold green] Completat (3.2s, 3,450 tokens, €0.0580)

[14:24:03] ⚠️  [bold yellow][Revisor][/bold yellow] Qualitat del chunk 2: 6.8/10

[14:24:03] ⏳ [bold cyan][Pipeline][/bold cyan] Processant chunk (3/15, 20%)
...

[14:28:45] 🚀 [bold blue][Pipeline][/bold blue] Fase 3: Fusionant traduccions...

[bold]══════════════════════════════════════════════════[/bold]
[bold green]📊 Resum de la sessió[/bold green]
[bold]══════════════════════════════════════════════════[/bold]
⏱️  Temps total: 300.2s
🔢 Crides totals: 45
📝 Tokens processats: 125,430
💰 Cost total: €2.1082
[bold]══════════════════════════════════════════════════[/bold]
"""

    for line in output_lines.strip().split('\n'):
        console.print(line)
        time.sleep(0.05)


def main():
    """Executa totes les demostracions."""
    console = Console()

    console.print(Panel.fit(
        "[bold magenta]SISTEMA DE LOGGING I VISUALITZACIÓ[/bold magenta]\n"
        "[dim]Editorial Clàssica - Demostració[/dim]",
        border_style="magenta",
    ))

    # Demo 1: Modes de logging
    demo_logging_modes()

    console.print("\n" + "─" * 60 + "\n")

    # Demo 2: Exemple d'output
    demo_progress_output()

    console.print("\n" + "─" * 60 + "\n")

    # Demo 3: Dashboard (opcional)
    from rich.prompt import Confirm
    if Confirm.ask("\n[bold]Vols veure la demostració del dashboard interactiu?[/bold]"):
        demo_dashboard()

    console.print("\n[bold green]Demostració completada![/bold green]")
    console.print("[dim]Revisa output/logs/ per veure els fitxers de log generats.[/dim]\n")


if __name__ == "__main__":
    main()
