#!/usr/bin/env python3
"""
Sistema de Logging per al Pipeline de Traducció
================================================

Proporciona logging detallat amb:
- Consola amb colors (Rich)
- Fitxer de log persistent
- Dashboard en temps real
- Estadístiques acumulades
- Webhooks opcionals (Slack, Discord)
"""

import json
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    MofNCompleteColumn,
)
from rich.table import Table
from rich.layout import Layout
from rich.text import Text


class LogLevel(str, Enum):
    """Nivells de logging."""
    DEBUG = "debug"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogColors:
    """Colors per a cada nivell."""
    DEBUG = "dim white"
    INFO = "blue"
    SUCCESS = "green"
    WARNING = "yellow"
    ERROR = "red"
    CRITICAL = "bold red on white"


class TranslationLogger:
    """Logger especialitzat per al pipeline de traducció."""

    def __init__(
        self,
        log_dir: Path | str = "output/logs",
        console_output: bool = True,
        file_output: bool = True,
        min_level: LogLevel = LogLevel.INFO,
        project_name: str = "Schopenhauer",
    ):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.console_output = console_output
        self.file_output = file_output
        self.min_level = min_level
        self.project_name = project_name

        # Consola Rich
        self.console = Console()

        # Fitxer de log
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"translation_{timestamp}.log"
        self.json_log_file = self.log_dir / f"translation_{timestamp}.jsonl"

        # Estadístiques
        self.stats = {
            "start_time": datetime.now(),
            "total_chunks": 0,
            "completed_chunks": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "errors": 0,
            "warnings": 0,
            "current_stage": "inicialitzant",
            "current_chunk": 0,
            "quality_scores": [],
        }

        # Callbacks
        self._callbacks: list[Callable[[dict], None]] = []

        # Escriure capçalera
        self._write_header()

    def _write_header(self):
        """Escriu capçalera als fitxers de log."""
        header = f"""
{'='*70}
 PIPELINE DE TRADUCCIÓ - {self.project_name}
 Iniciat: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}
{'='*70}
"""
        if self.file_output:
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.write(header)

    def _get_level_priority(self, level: LogLevel) -> int:
        """Retorna prioritat numèrica del nivell."""
        priorities = {
            LogLevel.DEBUG: 0,
            LogLevel.INFO: 1,
            LogLevel.SUCCESS: 2,
            LogLevel.WARNING: 3,
            LogLevel.ERROR: 4,
            LogLevel.CRITICAL: 5,
        }
        return priorities.get(level, 1)

    def _should_log(self, level: LogLevel) -> bool:
        """Determina si s'ha de registrar aquest nivell."""
        return self._get_level_priority(level) >= self._get_level_priority(self.min_level)

    def _get_color(self, level: LogLevel) -> str:
        """Retorna color per al nivell."""
        return getattr(LogColors, level.value.upper(), "white")

    def _format_message(self, level: LogLevel, stage: str, message: str) -> str:
        """Formata missatge per a fitxer."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        return f"[{timestamp}] [{level.value.upper():8}] [{stage:15}] {message}"

    def _log(
        self,
        level: LogLevel,
        stage: str,
        message: str,
        data: dict | None = None,
    ):
        """Registra un missatge."""
        if not self._should_log(level):
            return

        timestamp = datetime.now()

        # Format per consola
        if self.console_output:
            color = self._get_color(level)
            time_str = timestamp.strftime("%H:%M:%S")

            # Icones per nivell
            icons = {
                LogLevel.DEBUG: "🔍",
                LogLevel.INFO: "ℹ️ ",
                LogLevel.SUCCESS: "✅",
                LogLevel.WARNING: "⚠️ ",
                LogLevel.ERROR: "❌",
                LogLevel.CRITICAL: "🚨",
            }
            icon = icons.get(level, "•")

            self.console.print(
                f"[dim]{time_str}[/dim] {icon} [{color}]{stage:15}[/{color}] {message}"
            )

        # Format per fitxer
        if self.file_output:
            log_line = self._format_message(level, stage, message)
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_line + "\n")

            # JSON log per anàlisi posterior
            json_entry = {
                "timestamp": timestamp.isoformat(),
                "level": level.value,
                "stage": stage,
                "message": message,
                "data": data,
            }
            with open(self.json_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(json_entry, ensure_ascii=False) + "\n")

        # Callbacks
        for callback in self._callbacks:
            try:
                callback({
                    "level": level.value,
                    "stage": stage,
                    "message": message,
                    "data": data,
                    "stats": self.stats.copy(),
                })
            except Exception:
                pass

    # Mètodes de conveniència
    def debug(self, stage: str, message: str, data: dict | None = None):
        self._log(LogLevel.DEBUG, stage, message, data)

    def info(self, stage: str, message: str, data: dict | None = None):
        self._log(LogLevel.INFO, stage, message, data)

    def success(self, stage: str, message: str, data: dict | None = None):
        self._log(LogLevel.SUCCESS, stage, message, data)

    def warning(self, stage: str, message: str, data: dict | None = None):
        self.stats["warnings"] += 1
        self._log(LogLevel.WARNING, stage, message, data)

    def error(self, stage: str, message: str, data: dict | None = None):
        self.stats["errors"] += 1
        self._log(LogLevel.ERROR, stage, message, data)

    def critical(self, stage: str, message: str, data: dict | None = None):
        self.stats["errors"] += 1
        self._log(LogLevel.CRITICAL, stage, message, data)

    # Mètodes específics del pipeline
    def start_pipeline(self, total_chunks: int, source_file: str):
        """Registra inici del pipeline."""
        self.stats["total_chunks"] = total_chunks
        self.stats["current_stage"] = "iniciant"

        self.console.print()
        self.console.print(Panel.fit(
            f"[bold cyan]PIPELINE DE TRADUCCIÓ[/bold cyan]\n"
            f"[yellow]{self.project_name}[/yellow]\n\n"
            f"📄 Font: {source_file}\n"
            f"📦 Chunks: {total_chunks}\n"
            f"🕐 Inici: {datetime.now().strftime('%H:%M:%S')}",
            title="🏛️ Editorial Clàssica",
            border_style="cyan",
        ))
        self.console.print()

        self.info("PIPELINE", f"Iniciant traducció amb {total_chunks} chunks")

    def start_stage(self, stage: str):
        """Registra inici d'una etapa."""
        self.stats["current_stage"] = stage
        self.info(stage.upper(), f"Iniciant etapa: {stage}")

    def start_chunk(self, chunk_num: int, chunk_size: int):
        """Registra inici d'un chunk."""
        self.stats["current_chunk"] = chunk_num
        self.info("CHUNK", f"Processant chunk {chunk_num}/{self.stats['total_chunks']} ({chunk_size:,} chars)")

    def complete_chunk(
        self,
        chunk_num: int,
        tokens: int,
        cost: float,
        quality: float,
        duration: float,
    ):
        """Registra finalització d'un chunk."""
        self.stats["completed_chunks"] += 1
        self.stats["total_tokens"] += tokens
        self.stats["total_cost"] += cost
        self.stats["quality_scores"].append(quality)

        avg_quality = sum(self.stats["quality_scores"]) / len(self.stats["quality_scores"])

        self.success(
            "CHUNK",
            f"Chunk {chunk_num} completat | "
            f"Qualitat: {quality:.1f}/10 | "
            f"Tokens: {tokens:,} | "
            f"Cost: €{cost:.4f} | "
            f"Temps: {duration:.1f}s",
            {
                "chunk": chunk_num,
                "tokens": tokens,
                "cost": cost,
                "quality": quality,
                "duration": duration,
            }
        )

        # Mostrar progrés
        progress = self.stats["completed_chunks"] / self.stats["total_chunks"] * 100
        self.console.print(
            f"    [dim]Progrés: {progress:.0f}% | "
            f"Mitjana qualitat: {avg_quality:.1f}/10 | "
            f"Cost acumulat: €{self.stats['total_cost']:.4f}[/dim]"
        )

    def log_translation(self, chunk_num: int, preview: str):
        """Registra preview de traducció."""
        preview_short = preview[:100].replace("\n", " ") + "..." if len(preview) > 100 else preview
        self.debug("TRADUCCIÓ", f"Chunk {chunk_num}: {preview_short}")

    def log_review(self, chunk_num: int, round_num: int, score: float, issues: int):
        """Registra resultat de revisió."""
        status = "✅" if score >= 7.0 else "⚠️" if score >= 5.0 else "❌"
        self.info(
            "REVISIÓ",
            f"Chunk {chunk_num} ronda {round_num} | {status} Puntuació: {score:.1f}/10 | Issues: {issues}"
        )

    def log_correction(self, chunk_num: int, corrections: int):
        """Registra correccions aplicades."""
        self.info("CORRECCIÓ", f"Chunk {chunk_num} | {corrections} correccions aplicades")

    def log_glossary(self, terms_count: int):
        """Registra generació de glossari."""
        self.success("GLOSSARI", f"Glossari generat amb {terms_count} termes")

    def log_api_call(self, agent: str, tokens_in: int, tokens_out: int, cost: float):
        """Registra crida a l'API."""
        self.debug(
            "API",
            f"{agent} | In: {tokens_in:,} | Out: {tokens_out:,} | Cost: €{cost:.4f}"
        )

    def log_cost_warning(self, current: float, limit: float):
        """Avís de cost."""
        percentage = (current / limit) * 100
        if percentage >= 90:
            self.warning("COST", f"⚠️ Cost al {percentage:.0f}% del límit (€{current:.2f}/€{limit:.2f})")
        elif percentage >= 75:
            self.info("COST", f"Cost al {percentage:.0f}% del límit (€{current:.2f}/€{limit:.2f})")

    def complete_pipeline(self):
        """Registra finalització del pipeline."""
        duration = (datetime.now() - self.stats["start_time"]).total_seconds()
        avg_quality = sum(self.stats["quality_scores"]) / len(self.stats["quality_scores"]) if self.stats["quality_scores"] else 0

        self.console.print()
        self.console.print(Panel.fit(
            f"[bold green]✅ TRADUCCIÓ COMPLETADA[/bold green]\n\n"
            f"📦 Chunks: {self.stats['completed_chunks']}/{self.stats['total_chunks']}\n"
            f"⭐ Qualitat mitjana: {avg_quality:.1f}/10\n"
            f"🔤 Tokens totals: {self.stats['total_tokens']:,}\n"
            f"💰 Cost total: €{self.stats['total_cost']:.4f}\n"
            f"⏱️ Durada: {duration/60:.1f} minuts\n"
            f"⚠️ Warnings: {self.stats['warnings']}\n"
            f"❌ Errors: {self.stats['errors']}",
            title="📊 Resum",
            border_style="green",
        ))

        self.success(
            "PIPELINE",
            f"Pipeline completat en {duration/60:.1f} min | "
            f"Qualitat: {avg_quality:.1f}/10 | "
            f"Cost: €{self.stats['total_cost']:.4f}"
        )

        # Guardar resum
        summary_file = self.log_dir / "summary.json"
        summary = {
            "project": self.project_name,
            "start_time": self.stats["start_time"].isoformat(),
            "end_time": datetime.now().isoformat(),
            "duration_seconds": duration,
            "total_chunks": self.stats["total_chunks"],
            "completed_chunks": self.stats["completed_chunks"],
            "total_tokens": self.stats["total_tokens"],
            "total_cost_eur": self.stats["total_cost"],
            "average_quality": avg_quality,
            "warnings": self.stats["warnings"],
            "errors": self.stats["errors"],
        }
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        return summary

    def add_callback(self, callback: Callable[[dict], None]):
        """Afegeix callback per a events de log."""
        self._callbacks.append(callback)

    def get_stats(self) -> dict:
        """Retorna estadístiques actuals."""
        return self.stats.copy()


class LiveDashboard:
    """Dashboard en temps real amb Rich."""

    def __init__(self, logger: TranslationLogger):
        self.logger = logger
        self.console = Console()
        self._live: Live | None = None

    def _generate_layout(self) -> Panel:
        """Genera el layout del dashboard."""
        stats = self.logger.get_stats()

        # Calcular valors
        progress = stats["completed_chunks"] / stats["total_chunks"] * 100 if stats["total_chunks"] > 0 else 0
        elapsed = (datetime.now() - stats["start_time"]).total_seconds()
        avg_quality = sum(stats["quality_scores"]) / len(stats["quality_scores"]) if stats["quality_scores"] else 0

        # Estimar temps restant
        if stats["completed_chunks"] > 0:
            time_per_chunk = elapsed / stats["completed_chunks"]
            remaining_chunks = stats["total_chunks"] - stats["completed_chunks"]
            eta_seconds = time_per_chunk * remaining_chunks
            eta_str = f"{eta_seconds/60:.0f} min"
        else:
            eta_str = "calculant..."

        # Crear taula
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="cyan")
        table.add_column(style="white")

        table.add_row("📦 Progrés", f"{stats['completed_chunks']}/{stats['total_chunks']} chunks ({progress:.0f}%)")
        table.add_row("⭐ Qualitat", f"{avg_quality:.1f}/10")
        table.add_row("🔤 Tokens", f"{stats['total_tokens']:,}")
        table.add_row("💰 Cost", f"€{stats['total_cost']:.4f}")
        table.add_row("⏱️ Temps", f"{elapsed/60:.1f} min")
        table.add_row("⏳ ETA", eta_str)
        table.add_row("📍 Etapa", stats["current_stage"])

        # Barra de progrés visual
        bar_width = 30
        filled = int(bar_width * progress / 100)
        bar = "█" * filled + "░" * (bar_width - filled)

        content = Text()
        content.append(f"\n{bar} {progress:.0f}%\n\n", style="green")

        return Panel(
            table,
            title=f"🏛️ {self.logger.project_name}",
            subtitle=f"[dim]{datetime.now().strftime('%H:%M:%S')}[/dim]",
            border_style="cyan",
        )

    def start(self):
        """Inicia el dashboard."""
        self._live = Live(
            self._generate_layout(),
            console=self.console,
            refresh_per_second=1,
        )
        self._live.start()

    def update(self):
        """Actualitza el dashboard."""
        if self._live:
            self._live.update(self._generate_layout())

    def stop(self):
        """Atura el dashboard."""
        if self._live:
            self._live.stop()


# Exemple d'ús
if __name__ == "__main__":
    # Crear logger
    logger = TranslationLogger(
        log_dir=Path("output/schopenhauer/logs"),
        project_name="Schopenhauer - Vierfache Wurzel",
        min_level=LogLevel.DEBUG,
    )

    # Simular pipeline
    logger.start_pipeline(total_chunks=10, source_file="fourfold_root_en.txt")

    logger.start_stage("glossari")
    logger.log_glossary(45)

    for i in range(1, 11):
        logger.start_chunk(i, chunk_size=2500)

        # Simular traducció
        import time
        time.sleep(0.5)

        logger.log_translation(i, "Aquesta dissertació filosòfica...")
        logger.log_review(i, 1, 7.5, 3)
        logger.log_correction(i, 5)

        logger.complete_chunk(
            chunk_num=i,
            tokens=1500,
            cost=0.045,
            quality=7.5 + (i % 3) * 0.5,
            duration=45.0,
        )

    logger.complete_pipeline()
