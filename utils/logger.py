"""Sistema de logging amb Rich per als agents de traducció."""

import logging
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.logging import RichHandler
from rich.text import Text


class VerbosityLevel(str, Enum):
    """Nivells de verbositat del sistema."""

    QUIET = "quiet"      # Només errors
    NORMAL = "normal"    # Progrés bàsic (default)
    VERBOSE = "verbose"  # Detall complet + logs
    DEBUG = "debug"      # Tot + temps d'execució + tokens


# Mapeig de nivells de verbositat a nivells de logging
VERBOSITY_TO_LOG_LEVEL = {
    VerbosityLevel.QUIET: logging.ERROR,
    VerbosityLevel.NORMAL: logging.INFO,
    VerbosityLevel.VERBOSE: logging.DEBUG,
    VerbosityLevel.DEBUG: logging.DEBUG,
}


# Icones per cada tipus d'agent
AGENT_ICONS = {
    "ConsellEditorial": "🏛️",
    "ChunkerAgent": "✂️",
    "Investigador": "🔍",
    "Traductor": "🌍",
    "TranslatorAgent": "🌍",
    "Corrector": "📝",
    "ReviewerAgent": "📝",
    "Pipeline": "🚀",
    "Dashboard": "📊",
    "default": "🤖",
}


# Colors per cada tipus de missatge
MESSAGE_COLORS = {
    "start": "cyan",
    "complete": "green",
    "error": "red",
    "warning": "yellow",
    "info": "blue",
    "debug": "dim",
    "cost": "magenta",
    "progress": "cyan",
}


class AgentLogger:
    """Logger específic per als agents amb format i colors Rich."""

    _instance: "AgentLogger | None" = None
    _initialized: bool = False

    def __new__(cls, *args: Any, **kwargs: Any) -> "AgentLogger":
        """Singleton pattern per assegurar un únic logger."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        verbosity: VerbosityLevel = VerbosityLevel.NORMAL,
        log_dir: Path | None = None,
        session_name: str | None = None,
    ) -> None:
        """Inicialitza el logger.

        Args:
            verbosity: Nivell de verbositat.
            log_dir: Directori on desar els logs.
            session_name: Nom de la sessió per al fitxer de log.
        """
        if AgentLogger._initialized:
            return

        self.verbosity = verbosity
        self.console = Console()
        self.log_dir = Path(log_dir) if log_dir else Path("output/logs")
        self.session_name = session_name or datetime.now().strftime("%Y%m%d_%H%M%S")

        # Crear directori de logs
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Configurar logging estàndard
        self._setup_logging()

        # Estadístiques de la sessió
        self.stats = SessionStats()

        AgentLogger._initialized = True

    def _setup_logging(self) -> None:
        """Configura el sistema de logging."""
        log_level = VERBOSITY_TO_LOG_LEVEL[self.verbosity]

        # Handler per consola amb Rich
        console_handler = RichHandler(
            console=self.console,
            show_time=True,
            show_path=False,
            rich_tracebacks=True,
            markup=True,
        )
        console_handler.setLevel(log_level)

        # Handler per fitxer
        log_file = self.log_dir / f"translation_{self.session_name}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # Sempre guardem tot al fitxer
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)

        # Configurar logger arrel
        root_logger = logging.getLogger("editorial")
        root_logger.setLevel(logging.DEBUG)
        root_logger.handlers = []  # Netejar handlers existents
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)

        self._logger = root_logger
        self._log_file = log_file

    def reconfigure(
        self,
        verbosity: VerbosityLevel | None = None,
        log_dir: Path | None = None,
        session_name: str | None = None,
    ) -> None:
        """Reconfigura el logger amb nous paràmetres."""
        AgentLogger._initialized = False
        if verbosity is not None:
            self.verbosity = verbosity
        if log_dir is not None:
            self.log_dir = log_dir
        if session_name is not None:
            self.session_name = session_name
        self._setup_logging()
        AgentLogger._initialized = True

    def get_icon(self, agent_name: str) -> str:
        """Retorna la icona per un agent."""
        return AGENT_ICONS.get(agent_name, AGENT_ICONS["default"])

    def _format_message(
        self,
        agent_name: str,
        message: str,
        msg_type: str = "info",
    ) -> Text:
        """Formata un missatge amb colors i icones."""
        icon = self.get_icon(agent_name)
        color = MESSAGE_COLORS.get(msg_type, "white")

        text = Text()
        text.append(f"{icon} ", style="bold")
        text.append(f"[{agent_name}] ", style=f"bold {color}")
        text.append(message, style=color)

        return text

    def log_start(self, agent_name: str, message: str) -> None:
        """Log quan un agent comença a processar."""
        if self.verbosity == VerbosityLevel.QUIET:
            return

        icon = self.get_icon(agent_name)
        self.console.print(f"{icon} [bold cyan][{agent_name}][/bold cyan] {message}")
        self._logger.info(f"[{agent_name}] START: {message}")

    def log_complete(
        self,
        agent_name: str,
        duration_seconds: float,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_eur: float = 0.0,
    ) -> None:
        """Log quan un agent completa el processament."""
        if self.verbosity == VerbosityLevel.QUIET:
            return

        # Actualitzar estadístiques
        self.stats.add_call(agent_name, duration_seconds, input_tokens, output_tokens, cost_eur)

        # Format del missatge segons verbositat
        parts = [f"Completat ({duration_seconds:.1f}s"]

        if self.verbosity in (VerbosityLevel.VERBOSE, VerbosityLevel.DEBUG):
            total_tokens = input_tokens + output_tokens
            if total_tokens > 0:
                parts.append(f", {total_tokens:,} tokens")
            if cost_eur > 0:
                parts.append(f", €{cost_eur:.4f}")

        parts.append(")")
        message = "".join(parts)

        self.console.print(f"✅ [bold green][{agent_name}][/bold green] {message}")
        self._logger.info(
            f"[{agent_name}] COMPLETE: {duration_seconds:.2f}s, "
            f"tokens_in={input_tokens}, tokens_out={output_tokens}, cost=€{cost_eur:.4f}"
        )

    def log_error(self, agent_name: str, error: str | Exception) -> None:
        """Log quan hi ha un error."""
        error_msg = str(error)
        icon = self.get_icon(agent_name)

        self.console.print(f"❌ [bold red][{agent_name}][/bold red] Error: {error_msg}")
        self._logger.error(f"[{agent_name}] ERROR: {error_msg}")

        self.stats.add_error(agent_name, error_msg)

    def log_warning(self, agent_name: str, message: str) -> None:
        """Log d'avís."""
        if self.verbosity == VerbosityLevel.QUIET:
            return

        self.console.print(f"⚠️  [bold yellow][{agent_name}][/bold yellow] {message}")
        self._logger.warning(f"[{agent_name}] WARNING: {message}")

    def log_info(self, agent_name: str, message: str) -> None:
        """Log informatiu."""
        if self.verbosity in (VerbosityLevel.QUIET,):
            return

        icon = self.get_icon(agent_name)
        self.console.print(f"{icon} [bold blue][{agent_name}][/bold blue] {message}")
        self._logger.info(f"[{agent_name}] INFO: {message}")

    def log_debug(self, agent_name: str, message: str) -> None:
        """Log de depuració (només en mode verbose/debug)."""
        if self.verbosity not in (VerbosityLevel.VERBOSE, VerbosityLevel.DEBUG):
            return

        self.console.print(f"🔧 [dim][{agent_name}][/dim] {message}", style="dim")
        self._logger.debug(f"[{agent_name}] DEBUG: {message}")

    def log_progress(
        self,
        agent_name: str,
        current: int,
        total: int,
        message: str = "",
    ) -> None:
        """Log de progrés."""
        if self.verbosity == VerbosityLevel.QUIET:
            return

        percentage = (current / total * 100) if total > 0 else 0
        icon = self.get_icon(agent_name)
        progress_msg = f"{message} ({current}/{total}, {percentage:.0f}%)" if message else f"{current}/{total} ({percentage:.0f}%)"

        self.console.print(f"⏳ [bold cyan][{agent_name}][/bold cyan] {progress_msg}")
        self._logger.info(f"[{agent_name}] PROGRESS: {progress_msg}")

    def log_cost_warning(self, current_cost: float, limit: float) -> None:
        """Avís quan el cost s'apropa al límit."""
        percentage = (current_cost / limit * 100) if limit > 0 else 0

        if percentage >= 90:
            self.console.print(
                f"🚨 [bold red]ALERTA:[/bold red] Cost (€{current_cost:.2f}) al "
                f"[bold]{percentage:.0f}%[/bold] del límit (€{limit:.2f})"
            )
        elif percentage >= 75:
            self.console.print(
                f"⚠️  [bold yellow]Avís:[/bold yellow] Cost (€{current_cost:.2f}) al "
                f"{percentage:.0f}% del límit (€{limit:.2f})"
            )

        self._logger.warning(f"COST WARNING: €{current_cost:.2f} / €{limit:.2f} ({percentage:.0f}%)")

    def log_session_start(
        self,
        work_title: str,
        author: str | None = None,
        estimated_cost: float | None = None,
    ) -> None:
        """Log d'inici de sessió de traducció."""
        self.console.print()
        self.console.print(f"🚀 [bold green]Iniciant traducció:[/bold green] {work_title}")

        if author:
            self.console.print(f"📚 [bold]Autor:[/bold] {author}")

        if estimated_cost is not None:
            self.console.print(f"💰 [bold]Cost estimat:[/bold] €{estimated_cost:.2f}")

        self.console.print()

        self._logger.info(f"SESSION START: {work_title} by {author}, estimated_cost=€{estimated_cost or 0:.2f}")

    def log_session_end(self) -> None:
        """Log de fi de sessió amb resum."""
        summary = self.stats.get_summary()

        self.console.print()
        self.console.print("[bold]═" * 50 + "[/bold]")
        self.console.print("[bold green]📊 Resum de la sessió[/bold green]")
        self.console.print("[bold]═" * 50 + "[/bold]")

        self.console.print(f"⏱️  Temps total: {summary['total_duration']:.1f}s")
        self.console.print(f"🔢 Crides totals: {summary['total_calls']}")
        self.console.print(f"📝 Tokens processats: {summary['total_tokens']:,}")
        self.console.print(f"💰 Cost total: €{summary['total_cost']:.4f}")

        if summary['errors']:
            self.console.print(f"❌ Errors: {len(summary['errors'])}")

        self.console.print("[bold]═" * 50 + "[/bold]")
        self.console.print()

        # Desar resum al fitxer
        self._logger.info(f"SESSION END: {summary}")
        self._save_summary(summary)

    def _save_summary(self, summary: dict[str, Any]) -> None:
        """Desa el resum de la sessió al fitxer de log."""
        summary_file = self.log_dir / f"summary_{self.session_name}.txt"

        lines = [
            "=" * 60,
            f"RESUM DE SESSIÓ: {self.session_name}",
            "=" * 60,
            "",
            f"Temps total: {summary['total_duration']:.1f}s",
            f"Crides totals: {summary['total_calls']}",
            f"Tokens processats: {summary['total_tokens']:,}",
            f"Cost total: €{summary['total_cost']:.4f}",
            "",
            "Crides per agent:",
        ]

        for agent, stats in summary.get("by_agent", {}).items():
            lines.append(f"  - {agent}: {stats['calls']} crides, {stats['tokens']:,} tokens, €{stats['cost']:.4f}")

        if summary["errors"]:
            lines.append("")
            lines.append("Errors:")
            for error in summary["errors"]:
                lines.append(f"  - [{error['agent']}] {error['error']}")

        lines.append("")
        lines.append("=" * 60)

        summary_file.write_text("\n".join(lines), encoding="utf-8")

    @property
    def log_file_path(self) -> Path:
        """Retorna el path del fitxer de log."""
        return self._log_file


class SessionStats:
    """Estadístiques de la sessió de traducció."""

    def __init__(self) -> None:
        self.start_time = datetime.now()
        self.calls: list[dict[str, Any]] = []
        self.errors: list[dict[str, Any]] = []
        self.by_agent: dict[str, dict[str, Any]] = {}

    def add_call(
        self,
        agent_name: str,
        duration: float,
        input_tokens: int,
        output_tokens: int,
        cost: float,
    ) -> None:
        """Registra una crida d'agent."""
        call_data = {
            "agent": agent_name,
            "timestamp": datetime.now(),
            "duration": duration,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
        }
        self.calls.append(call_data)

        # Actualitzar estadístiques per agent
        if agent_name not in self.by_agent:
            self.by_agent[agent_name] = {
                "calls": 0,
                "duration": 0.0,
                "tokens": 0,
                "cost": 0.0,
            }

        agent_stats = self.by_agent[agent_name]
        agent_stats["calls"] += 1
        agent_stats["duration"] += duration
        agent_stats["tokens"] += input_tokens + output_tokens
        agent_stats["cost"] += cost

    def add_error(self, agent_name: str, error: str) -> None:
        """Registra un error."""
        self.errors.append({
            "agent": agent_name,
            "timestamp": datetime.now(),
            "error": error,
        })

    def get_summary(self) -> dict[str, Any]:
        """Retorna un resum de les estadístiques."""
        total_duration = sum(c["duration"] for c in self.calls)
        total_tokens = sum(c["input_tokens"] + c["output_tokens"] for c in self.calls)
        total_cost = sum(c["cost"] for c in self.calls)

        return {
            "session_start": self.start_time.isoformat(),
            "session_end": datetime.now().isoformat(),
            "total_calls": len(self.calls),
            "total_duration": total_duration,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "by_agent": self.by_agent,
            "errors": self.errors,
        }


# Funció de conveniència per obtenir el logger
def get_logger(
    verbosity: VerbosityLevel = VerbosityLevel.NORMAL,
    log_dir: Path | None = None,
    session_name: str | None = None,
) -> AgentLogger:
    """Obté o crea el logger singleton.

    Args:
        verbosity: Nivell de verbositat.
        log_dir: Directori on desar els logs.
        session_name: Nom de la sessió.

    Returns:
        Instància del logger.
    """
    return AgentLogger(verbosity=verbosity, log_dir=log_dir, session_name=session_name)


def reset_logger() -> None:
    """Reinicia el logger singleton (útil per a tests)."""
    AgentLogger._instance = None
    AgentLogger._initialized = False
