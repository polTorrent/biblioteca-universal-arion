"""Orquestrador del flux de debugging TDD.

Coordina BugReproducerAgent i BugFixerAgent per reproduir i arreglar bugs
seguint el principi Test-Driven Development.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table

from agents.base_agent import AgentConfig
from agents.debug.bug_fixer import BugFixerAgent
from agents.debug.bug_reproducer import BugReproducerAgent
from agents.debug.models import DebugResult


class DebugOrchestrator:
    """Orquestrador del flux de debugging.

    Coordina el procés complet de:
    1. Reproduir el bug amb un test que falla (BugReproducerAgent)
    2. Arreglar el bug fins que el test passi (BugFixerAgent)

    Example:
        >>> orchestrator = DebugOrchestrator()
        >>> result = orchestrator.debug(
        ...     descripcio="El càlcul retorna 0 amb decimals",
        ...     fitxers_context=["src/calculator.py"]
        ... )
        >>> print(result.resum())
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        base_dir: Path | None = None,
        verbose: bool = False,
    ) -> None:
        """Inicialitza l'orquestrador.

        Args:
            config: Configuració per als agents.
            base_dir: Directori base del projecte.
            verbose: Si s'ha de mostrar output detallat.
        """
        self.config = config or AgentConfig()
        self.base_dir = base_dir or Path.cwd()
        self.verbose = verbose
        self.console = Console()

        # Inicialitzar agents
        self.reproducer = BugReproducerAgent(config=self.config, base_dir=self.base_dir)
        self.fixer = BugFixerAgent(config=self.config, base_dir=self.base_dir)

    def _print_header(self, text: str) -> None:
        """Mostra una capçalera formatada."""
        self.console.print(Panel(text, style="bold blue"))

    def _print_success(self, text: str) -> None:
        """Mostra un missatge d'èxit."""
        self.console.print(f"[green]{text}[/green]")

    def _print_error(self, text: str) -> None:
        """Mostra un missatge d'error."""
        self.console.print(f"[red]{text}[/red]")

    def _print_warning(self, text: str) -> None:
        """Mostra un missatge d'avís."""
        self.console.print(f"[yellow]{text}[/yellow]")

    def _print_info(self, text: str) -> None:
        """Mostra informació si verbose està activat."""
        if self.verbose:
            self.console.print(f"[dim]{text}[/dim]")

    def debug(
        self,
        descripcio: str,
        fitxers_context: list[str | Path] | None = None,
        dry_run: bool = False,
        auto_commit: bool = False,
    ) -> DebugResult:
        """Executa el flux complet de debugging.

        Args:
            descripcio: Descripció del bug a arreglar.
            fitxers_context: Fitxers de codi relacionats.
            dry_run: Si True, només reprodueix sense arreglar.
            auto_commit: Si True, fa commit automàtic si el fix és exitós.

        Returns:
            DebugResult amb el resultat complet.
        """
        start_time = time.time()
        fitxers_context = fitxers_context or []

        self._print_header("Debug Orchestrator - Flux TDD")
        self.console.print()

        # Fase 1: Reproduir el bug
        self.console.print("[bold]Fase 1: Reproduir el bug[/bold]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True,
        ) as progress:
            task = progress.add_task("Analitzant i creant test...", total=None)

            try:
                bug_report = self.reproducer.reproduce(
                    descripcio=descripcio,
                    fitxers_context=fitxers_context,
                    guardar_test=True,
                )
                progress.update(task, completed=True)
            except Exception as e:
                progress.update(task, completed=True)
                self._print_error(f"Error reproduint bug: {e}")
                return DebugResult(
                    bug_report=None,
                    dry_run=dry_run,
                    temps_total=time.time() - start_time,
                )

        # Mostrar resultat de reproducció
        self._print_success("Bug reproduït correctament!")

        table = Table(show_header=False, box=None)
        table.add_column("Camp", style="cyan")
        table.add_column("Valor")
        table.add_row("Fitxer", str(bug_report.fitxer_afectat))
        table.add_row("Funció", bug_report.funcio_afectada)
        table.add_row("Severitat", bug_report.severitat)
        table.add_row("Test", str(bug_report.test_file) if bug_report.test_file else "temporal")
        self.console.print(table)

        if self.verbose:
            self.console.print("\n[bold]Test generat:[/bold]")
            self.console.print(Syntax(bug_report.test_code, "python", theme="monokai", line_numbers=True))

        # Si és dry_run, acabem aquí
        if dry_run:
            self._print_warning("\n[Mode dry-run: no s'apliquen canvis]")
            return DebugResult(
                bug_report=bug_report,
                dry_run=True,
                temps_total=time.time() - start_time,
            )

        # Fase 2: Arreglar el bug
        self.console.print("\n[bold]Fase 2: Arreglar el bug[/bold]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True,
        ) as progress:
            task = progress.add_task("Analitzant i proposant fix...", total=None)

            try:
                bug_fix = self.fixer.fix(
                    bug_report=bug_report,
                    aplicar_canvis=True,
                    revertir_si_falla=True,
                )
                progress.update(task, completed=True)
            except Exception as e:
                progress.update(task, completed=True)
                self._print_error(f"Error arreglant bug: {e}")
                return DebugResult(
                    bug_report=bug_report,
                    dry_run=False,
                    temps_total=time.time() - start_time,
                )

        # Mostrar resultat del fix
        if bug_fix.test_passa:
            self._print_success(f"Bug arreglat en {bug_fix.intents} intent(s)!")

            if self.verbose and bug_fix.diff:
                self.console.print("\n[bold]Diff aplicat:[/bold]")
                self.console.print(Syntax(bug_fix.diff, "diff", theme="monokai"))

            self.console.print(f"\n[bold]Explicació:[/bold] {bug_fix.explicacio}")

            # Auto-commit si està activat
            if auto_commit:
                self._auto_commit(bug_report, bug_fix)

        else:
            self._print_error(f"No s'ha pogut arreglar després de {bug_fix.intents} intent(s)")
            if bug_fix.error_test:
                self.console.print(f"\n[dim]Últim error:[/dim]\n{bug_fix.error_test[:500]}")

        # Resultat final
        temps_total = time.time() - start_time
        result = DebugResult(
            bug_report=bug_report,
            bug_fix=bug_fix,
            dry_run=False,
            temps_total=temps_total,
        )

        self.console.print()
        self.console.print(Panel(
            f"[{'green' if result.exit else 'red'}]"
            f"{'ÈXIT' if result.exit else 'FALLADA'}[/] "
            f"en {temps_total:.1f}s",
            style="bold",
        ))

        return result

    def _auto_commit(self, bug_report, bug_fix) -> bool:
        """Fa un commit automàtic del fix.

        Args:
            bug_report: Informe del bug.
            bug_fix: Fix aplicat.

        Returns:
            True si el commit s'ha fet correctament.
        """
        try:
            # Afegir fitxer modificat
            subprocess.run(
                ["git", "add", str(bug_fix.fitxer_modificat)],
                cwd=str(self.base_dir),
                check=True,
                capture_output=True,
            )

            # Crear missatge de commit
            commit_msg = f"""fix: {bug_report.descripcio[:50]}

Arreglat bug a {bug_report.funcio_afectada} ({bug_report.fitxer_afectat})

{bug_fix.explicacio}

Co-Authored-By: BugFixerAgent <noreply@biblioteca-arion.cat>
"""

            # Fer commit
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=str(self.base_dir),
                check=True,
                capture_output=True,
            )

            self._print_success("Commit creat automàticament")
            return True

        except subprocess.CalledProcessError as e:
            self._print_warning(f"No s'ha pogut fer auto-commit: {e}")
            return False


def main() -> None:
    """Punt d'entrada per CLI."""
    import os
    os.environ["CLAUDECODE"] = "1"

    parser = argparse.ArgumentParser(
        description="Debug Orchestrator - Sistema TDD per detectar i arreglar bugs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python -m agents.debug "El càlcul retorna 0 amb decimals"
  python -m agents.debug "Error amb textos buits" --files src/utils.py --verbose
  python -m agents.debug "Bug al parser" --dry-run
  python -m agents.debug "Falla amb None" --files module.py --auto-commit
        """,
    )

    parser.add_argument(
        "descripcio",
        help="Descripció del bug a arreglar",
    )
    parser.add_argument(
        "--files", "-f",
        nargs="+",
        help="Fitxers de context per analitzar",
        default=[],
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Només reproduir el bug, no arreglar",
    )
    parser.add_argument(
        "--auto-commit", "-c",
        action="store_true",
        help="Fer commit automàtic si el fix és exitós",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mostrar output detallat",
    )
    parser.add_argument(
        "--base-dir", "-d",
        type=Path,
        help="Directori base del projecte",
        default=None,
    )

    args = parser.parse_args()

    # Crear orquestrador
    orchestrator = DebugOrchestrator(
        base_dir=args.base_dir,
        verbose=args.verbose,
    )

    # Executar debugging
    result = orchestrator.debug(
        descripcio=args.descripcio,
        fitxers_context=args.files,
        dry_run=args.dry_run,
        auto_commit=args.auto_commit,
    )

    # Exit code basat en resultat
    sys.exit(0 if result.exit else 1)


if __name__ == "__main__":
    main()
