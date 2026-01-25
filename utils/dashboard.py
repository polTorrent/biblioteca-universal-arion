"""Dashboard interactiu en temps real per al pipeline de traducció."""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text


@dataclass
class AgentStatus:
    """Estat d'un agent."""

    name: str
    status: str = "idle"  # idle, processing, completed, error
    current_task: str = ""
    start_time: datetime | None = None
    end_time: datetime | None = None
    tokens_processed: int = 0
    cost: float = 0.0
    progress: int = 0
    total: int = 0


@dataclass
class DashboardState:
    """Estat complet del dashboard."""

    work_title: str = ""
    author: str = ""
    source_language: str = ""

    # Progrés global
    current_stage: str = "Preparant"
    global_progress: int = 0
    total_stages: int = 5
    current_chunk: int = 0
    total_chunks: int = 0

    # Agent actiu
    active_agent: str = ""
    agent_status: str = ""
    agent_progress: int = 0
    agent_total: int = 0

    # Estadístiques
    total_tokens: int = 0
    total_cost: float = 0.0
    words_translated: int = 0

    # Temps
    start_time: datetime = field(default_factory=datetime.now)
    estimated_remaining: float = 0.0

    # Agents
    agents: dict[str, AgentStatus] = field(default_factory=dict)

    # Errors/avisos
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class Dashboard:
    """Dashboard interactiu amb Rich per monitoritzar el pipeline."""

    def __init__(
        self,
        work_title: str = "",
        author: str = "",
        source_language: str = "llatí",
        total_chunks: int = 1,
    ) -> None:
        """Inicialitza el dashboard.

        Args:
            work_title: Títol de l'obra.
            author: Autor de l'obra.
            source_language: Llengua d'origen.
            total_chunks: Nombre total de chunks.
        """
        self.console = Console()
        self.state = DashboardState(
            work_title=work_title,
            author=author,
            source_language=source_language,
            total_chunks=total_chunks,
            start_time=datetime.now(),
        )

        self._live: Live | None = None
        self._progress: Progress | None = None
        self._global_task: TaskID | None = None
        self._chunk_task: TaskID | None = None
        self._agent_task: TaskID | None = None

    def _create_header_panel(self) -> Panel:
        """Crea el panell de capçalera."""
        title = self.state.work_title or "Traducció en curs"
        if self.state.author:
            title += f" - {self.state.author}"

        # Progress bar global
        progress_pct = (
            self.state.global_progress / self.state.total_stages * 100
            if self.state.total_stages > 0 else 0
        )
        bar_filled = int(progress_pct / 10)
        bar_empty = 10 - bar_filled
        progress_bar = "█" * bar_filled + "░" * bar_empty

        # Chunk progress
        chunk_info = ""
        if self.state.total_chunks > 1:
            chunk_info = f"\nChunk actual: {self.state.current_chunk}/{self.state.total_chunks}"

        content = f"""[bold]{title}[/bold]
Progrés global: [{progress_bar}] {progress_pct:.0f}%{chunk_info}"""

        return Panel(
            content,
            title="[bold cyan]EDITORIAL CLÀSSICA[/bold cyan]",
            border_style="cyan",
        )

    def _create_agent_panel(self) -> Panel:
        """Crea el panell de l'agent actiu."""
        if not self.state.active_agent:
            content = "[dim]Cap agent actiu[/dim]"
        else:
            # Progress de l'agent
            if self.state.agent_total > 0:
                pct = self.state.agent_progress / self.state.agent_total * 100
                bar_filled = int(pct / 5)
                bar_empty = 20 - bar_filled
                progress_bar = "█" * bar_filled + "░" * bar_empty
                progress_str = f"\n[{progress_bar}] {pct:.0f}%"
            else:
                progress_str = ""

            # Temps
            elapsed = (datetime.now() - self.state.start_time).total_seconds()
            elapsed_str = self._format_time(elapsed)
            remaining_str = self._format_time(self.state.estimated_remaining) if self.state.estimated_remaining > 0 else "calculant..."

            content = f"""Agent actiu: [bold cyan]{self.state.active_agent}[/bold cyan]
Estat: {self.state.agent_status}{progress_str}
Temps: {elapsed_str} / ~{remaining_str}"""

        return Panel(
            content,
            title="[bold yellow]Agent[/bold yellow]",
            border_style="yellow",
        )

    def _create_stats_panel(self) -> Panel:
        """Crea el panell d'estadístiques."""
        content = f"""[cyan]•[/cyan] Tokens processats: [bold]{self.state.total_tokens:,}[/bold]
[cyan]•[/cyan] Cost acumulat: [bold]€{self.state.total_cost:.4f}[/bold]
[cyan]•[/cyan] Paraules traduïdes: [bold]{self.state.words_translated:,}[/bold]"""

        return Panel(
            content,
            title="[bold green]Estadístiques[/bold green]",
            border_style="green",
        )

    def _create_warnings_panel(self) -> Panel | None:
        """Crea el panell d'avisos si n'hi ha."""
        if not self.state.warnings and not self.state.errors:
            return None

        lines = []
        for error in self.state.errors[-3:]:
            lines.append(f"[red]✗[/red] {error}")
        for warning in self.state.warnings[-3:]:
            lines.append(f"[yellow]⚠[/yellow] {warning}")

        return Panel(
            "\n".join(lines),
            title="[bold red]Avisos[/bold red]",
            border_style="red",
        )

    def _create_layout(self) -> Panel:
        """Crea el layout complet del dashboard."""
        # Crear el contingut
        header = self._create_header_panel()
        agent = self._create_agent_panel()
        stats = self._create_stats_panel()
        warnings = self._create_warnings_panel()

        # Combinar panels
        panels = [header, agent, stats]
        if warnings:
            panels.append(warnings)

        return Panel(
            Group(*panels),
            title="[bold white on blue] DASHBOARD [/bold white on blue]",
            border_style="blue",
        )

    def _format_time(self, seconds: float) -> str:
        """Formata segons a format llegible."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        if minutes < 60:
            return f"{minutes}m {secs}s"
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h {mins}m"

    def start(self) -> None:
        """Inicia el dashboard en mode live."""
        self._live = Live(
            self._create_layout(),
            console=self.console,
            refresh_per_second=4,
            transient=False,
        )
        self._live.start()

    def stop(self) -> None:
        """Atura el dashboard."""
        if self._live:
            self._live.stop()
            self._live = None

    def update(self) -> None:
        """Actualitza el dashboard."""
        if self._live:
            self._live.update(self._create_layout())

    def set_stage(self, stage: str, progress: int | None = None) -> None:
        """Actualitza l'etapa actual."""
        self.state.current_stage = stage
        if progress is not None:
            self.state.global_progress = progress
        self.update()

    def set_chunk(self, current: int, total: int | None = None) -> None:
        """Actualitza el chunk actual."""
        self.state.current_chunk = current
        if total is not None:
            self.state.total_chunks = total
        self.update()

    def set_active_agent(
        self,
        agent_name: str,
        status: str = "Processant...",
        progress: int = 0,
        total: int = 0,
    ) -> None:
        """Actualitza l'agent actiu."""
        self.state.active_agent = agent_name
        self.state.agent_status = status
        self.state.agent_progress = progress
        self.state.agent_total = total
        self.update()

    def update_agent_progress(self, progress: int, total: int | None = None) -> None:
        """Actualitza el progrés de l'agent actiu."""
        self.state.agent_progress = progress
        if total is not None:
            self.state.agent_total = total
        self.update()

    def add_tokens(self, tokens: int) -> None:
        """Afegeix tokens processats."""
        self.state.total_tokens += tokens
        self.update()

    def add_cost(self, cost: float) -> None:
        """Afegeix cost."""
        self.state.total_cost += cost
        self.update()

    def add_words(self, words: int) -> None:
        """Afegeix paraules traduïdes."""
        self.state.words_translated += words
        self.update()

    def set_estimated_remaining(self, seconds: float) -> None:
        """Estableix el temps estimat restant."""
        self.state.estimated_remaining = seconds
        self.update()

    def add_warning(self, warning: str) -> None:
        """Afegeix un avís."""
        self.state.warnings.append(warning)
        if len(self.state.warnings) > 10:
            self.state.warnings = self.state.warnings[-10:]
        self.update()

    def add_error(self, error: str) -> None:
        """Afegeix un error."""
        self.state.errors.append(error)
        if len(self.state.errors) > 10:
            self.state.errors = self.state.errors[-10:]
        self.update()

    def agent_complete(
        self,
        agent_name: str,
        duration: float,
        tokens: int,
        cost: float,
    ) -> None:
        """Marca un agent com a completat."""
        if agent_name not in self.state.agents:
            self.state.agents[agent_name] = AgentStatus(name=agent_name)

        agent = self.state.agents[agent_name]
        agent.status = "completed"
        agent.end_time = datetime.now()
        agent.tokens_processed = tokens
        agent.cost = cost

        self.add_tokens(tokens)
        self.add_cost(cost)
        self.update()

    def __enter__(self) -> "Dashboard":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.stop()


class ProgressTracker:
    """Tracker de progrés simplificat per al pipeline."""

    def __init__(
        self,
        console: Console | None = None,
        show_time: bool = True,
        show_speed: bool = False,
    ) -> None:
        """Inicialitza el tracker.

        Args:
            console: Consola Rich.
            show_time: Mostrar temps transcorregut.
            show_speed: Mostrar velocitat de processament.
        """
        self.console = console or Console()
        self.show_time = show_time
        self.show_speed = show_speed

        columns = [
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            MofNCompleteColumn(),
        ]

        if show_time:
            columns.extend([TimeElapsedColumn(), TimeRemainingColumn()])

        self._progress = Progress(*columns, console=self.console)
        self._tasks: dict[str, TaskID] = {}

    def start(self) -> None:
        """Inicia el tracker."""
        self._progress.start()

    def stop(self) -> None:
        """Atura el tracker."""
        self._progress.stop()

    def add_task(
        self,
        name: str,
        description: str,
        total: int,
        completed: int = 0,
    ) -> str:
        """Afegeix una tasca al tracker."""
        task_id = self._progress.add_task(
            description,
            total=total,
            completed=completed,
        )
        self._tasks[name] = task_id
        return name

    def update_task(
        self,
        name: str,
        advance: int = 0,
        completed: int | None = None,
        description: str | None = None,
        total: int | None = None,
    ) -> None:
        """Actualitza una tasca."""
        if name not in self._tasks:
            return

        task_id = self._tasks[name]
        kwargs: dict[str, Any] = {}

        if completed is not None:
            kwargs["completed"] = completed
        if description is not None:
            kwargs["description"] = description
        if total is not None:
            kwargs["total"] = total

        if advance > 0:
            self._progress.update(task_id, advance=advance, **kwargs)
        elif kwargs:
            self._progress.update(task_id, **kwargs)

    def complete_task(self, name: str) -> None:
        """Marca una tasca com a completada."""
        if name not in self._tasks:
            return

        task_id = self._tasks[name]
        task = self._progress.tasks[task_id]
        self._progress.update(task_id, completed=task.total)

    def remove_task(self, name: str) -> None:
        """Elimina una tasca."""
        if name in self._tasks:
            self._progress.remove_task(self._tasks[name])
            del self._tasks[name]

    def __enter__(self) -> "ProgressTracker":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.stop()


def create_summary_table(
    title: str,
    rows: list[tuple[str, str]],
    title_style: str = "cyan",
    value_style: str = "green",
) -> Table:
    """Crea una taula de resum formatada.

    Args:
        title: Títol de la taula.
        rows: Llista de tuples (etiqueta, valor).
        title_style: Estil per la columna d'etiquetes.
        value_style: Estil per la columna de valors.

    Returns:
        Taula Rich formatada.
    """
    table = Table(title=title)
    table.add_column("Propietat", style=title_style)
    table.add_column("Valor", style=value_style)

    for label, value in rows:
        table.add_row(label, value)

    return table


def print_agent_activity(
    console: Console,
    agent_name: str,
    action: str,
    details: str = "",
    icon: str = "",
) -> None:
    """Imprimeix activitat d'un agent de forma formatada.

    Args:
        console: Consola Rich.
        agent_name: Nom de l'agent.
        action: Acció en curs.
        details: Detalls addicionals.
        icon: Icona a mostrar.
    """
    timestamp = datetime.now().strftime("%H:%M:%S")

    line = f"[dim][{timestamp}][/dim] {icon} [bold cyan]{agent_name}:[/bold cyan] {action}"
    if details:
        line += f" [dim]{details}[/dim]"

    console.print(line)
