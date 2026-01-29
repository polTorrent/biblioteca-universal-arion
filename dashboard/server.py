#!/usr/bin/env python3
"""Dashboard web per monitoritzar traduccions en temps real.

Obre automàticament al navegador i mostra:
- Progrés del pipeline
- Logs detallats
- Mètriques i gràfiques
"""

import json
import queue
import threading
import webbrowser
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from flask import Flask, render_template, Response, jsonify


# =============================================================================
# MODELS
# =============================================================================

class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


@dataclass
class LogEntry:
    timestamp: str
    level: LogLevel
    agent: str
    message: str
    details: Optional[dict] = None


@dataclass
class ChunkProgress:
    chunk_id: int
    total_chunks: int
    stage: str  # analitzant, traduint, avaluant, refinant, completat
    quality: Optional[float] = None
    iterations: int = 0


@dataclass
class PipelineMetrics:
    start_time: str
    elapsed_seconds: float = 0
    tokens_input: int = 0
    tokens_output: int = 0
    chunks_completed: int = 0
    chunks_total: int = 0
    avg_quality: float = 0
    current_stage: str = "iniciant"
    quality_history: list = field(default_factory=list)


@dataclass
class DashboardState:
    """Estat complet del dashboard."""
    obra: str = ""
    autor: str = ""
    llengua: str = ""
    metrics: PipelineMetrics = field(default_factory=lambda: PipelineMetrics(
        start_time=datetime.now().isoformat()
    ))
    chunks: list[ChunkProgress] = field(default_factory=list)
    logs: list[LogEntry] = field(default_factory=list)
    status: str = "pendent"  # pendent, executant, completat, error


# =============================================================================
# DASHBOARD SINGLETON
# =============================================================================

class TranslationDashboard:
    """Singleton per gestionar el dashboard de traducció."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.state = DashboardState()
        self.event_queue: queue.Queue = queue.Queue()
        self.app = self._create_app()
        self.server_thread: Optional[threading.Thread] = None
        self.port = 5050
        self._running = False

    def _create_app(self) -> Flask:
        """Crea l'aplicació Flask."""
        template_dir = Path(__file__).parent / "templates"
        static_dir = Path(__file__).parent / "static"

        app = Flask(
            __name__,
            template_folder=str(template_dir),
            static_folder=str(static_dir)
        )

        @app.route("/")
        def index():
            return render_template("dashboard.html")

        @app.route("/api/state")
        def get_state():
            return jsonify(self._state_to_dict())

        @app.route("/api/events")
        def events():
            def generate():
                while self._running:
                    try:
                        event = self.event_queue.get(timeout=1)
                        yield f"data: {json.dumps(event)}\n\n"
                    except queue.Empty:
                        # Heartbeat
                        yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

            return Response(
                generate(),
                mimetype="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )

        return app

    def _state_to_dict(self) -> dict:
        """Converteix l'estat a diccionari."""
        return {
            "obra": self.state.obra,
            "autor": self.state.autor,
            "llengua": self.state.llengua,
            "status": self.state.status,
            "metrics": asdict(self.state.metrics),
            "chunks": [asdict(c) for c in self.state.chunks],
            "logs": [asdict(l) for l in self.state.logs[-100:]],  # Últims 100 logs
        }

    def start(self, obra: str = "", autor: str = "", llengua: str = "", open_browser: bool = True):
        """Inicia el servidor del dashboard."""
        if self._running:
            return

        self.state = DashboardState(
            obra=obra,
            autor=autor,
            llengua=llengua,
            metrics=PipelineMetrics(start_time=datetime.now().isoformat()),
            status="executant"
        )
        self._running = True

        def run_server():
            self.app.run(
                host="127.0.0.1",
                port=self.port,
                debug=False,
                use_reloader=False,
                threaded=True
            )

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

        if open_browser:
            # Esperar que el servidor estigui llest
            import time
            time.sleep(0.5)
            webbrowser.open(f"http://127.0.0.1:{self.port}")

    def stop(self):
        """Atura el dashboard."""
        self._running = False
        self.state.status = "completat"
        self._send_event("status", {"status": "completat"})

    def _send_event(self, event_type: str, data: dict):
        """Envia un event al client."""
        self.event_queue.put({"type": event_type, **data})

    # =========================================================================
    # API PÚBLICA PER AL PIPELINE
    # =========================================================================

    def log(self, level: LogLevel, agent: str, message: str, details: dict = None):
        """Afegeix una entrada al log."""
        entry = LogEntry(
            timestamp=datetime.now().strftime("%H:%M:%S"),
            level=level,
            agent=agent,
            message=message,
            details=details
        )
        self.state.logs.append(entry)
        self._send_event("log", asdict(entry))

    def log_info(self, agent: str, message: str, details: dict = None):
        self.log(LogLevel.INFO, agent, message, details)

    def log_success(self, agent: str, message: str, details: dict = None):
        self.log(LogLevel.SUCCESS, agent, message, details)

    def log_warning(self, agent: str, message: str, details: dict = None):
        self.log(LogLevel.WARNING, agent, message, details)

    def log_error(self, agent: str, message: str, details: dict = None):
        self.log(LogLevel.ERROR, agent, message, details)

    def set_stage(self, stage: str):
        """Actualitza l'etapa actual."""
        self.state.metrics.current_stage = stage
        self._send_event("stage", {"stage": stage})

    def set_chunks(self, total: int):
        """Inicialitza els chunks."""
        self.state.metrics.chunks_total = total
        self.state.chunks = [
            ChunkProgress(chunk_id=i, total_chunks=total, stage="pendent")
            for i in range(total)
        ]
        self._send_event("chunks_init", {"total": total})

    def update_chunk(self, chunk_id: int, stage: str, quality: float = None, iterations: int = 0):
        """Actualitza l'estat d'un chunk."""
        if 0 <= chunk_id < len(self.state.chunks):
            chunk = self.state.chunks[chunk_id]
            chunk.stage = stage
            chunk.quality = quality
            chunk.iterations = iterations

            if stage == "completat":
                self.state.metrics.chunks_completed += 1
                if quality:
                    self.state.metrics.quality_history.append(quality)
                    self.state.metrics.avg_quality = sum(self.state.metrics.quality_history) / len(self.state.metrics.quality_history)

            self._send_event("chunk_update", {
                "chunk_id": chunk_id,
                "stage": stage,
                "quality": quality,
                "iterations": iterations,
                "completed": self.state.metrics.chunks_completed,
                "total": self.state.metrics.chunks_total,
                "avg_quality": self.state.metrics.avg_quality,
            })

    def update_tokens(self, input_tokens: int = 0, output_tokens: int = 0):
        """Actualitza el comptador de tokens."""
        self.state.metrics.tokens_input += input_tokens
        self.state.metrics.tokens_output += output_tokens
        self._send_event("tokens", {
            "input": self.state.metrics.tokens_input,
            "output": self.state.metrics.tokens_output,
        })

    def update_elapsed(self, seconds: float):
        """Actualitza el temps transcorregut."""
        self.state.metrics.elapsed_seconds = seconds
        self._send_event("elapsed", {"seconds": seconds})


# Instància global
dashboard = TranslationDashboard()


# =============================================================================
# FUNCIONS D'ÚS RÀPID
# =============================================================================

def start_dashboard(obra: str = "", autor: str = "", llengua: str = "", open_browser: bool = True):
    """Inicia el dashboard."""
    dashboard.start(obra, autor, llengua, open_browser)
    return dashboard


def stop_dashboard():
    """Atura el dashboard."""
    dashboard.stop()


if __name__ == "__main__":
    # Test
    import time

    dash = start_dashboard(
        obra="El biombo de l'infern",
        autor="Akutagawa",
        llengua="japonès"
    )

    dash.set_stage("glossari")
    dash.log_info("Glossarista", "Creant glossari terminològic...")
    time.sleep(2)

    dash.set_chunks(5)

    for i in range(5):
        dash.update_chunk(i, "traduint")
        dash.log_info("Traductor", f"Traduint chunk {i+1}/5...")
        time.sleep(1)

        dash.update_chunk(i, "avaluant")
        time.sleep(0.5)

        quality = 7.5 + (i * 0.3)
        dash.update_chunk(i, "completat", quality=quality, iterations=1)
        dash.log_success("Avaluador", f"Chunk {i+1} completat amb qualitat {quality:.1f}")

    dash.set_stage("completat")
    dash.log_success("Pipeline", "Traducció completada!")

    input("Prem Enter per tancar...")
    stop_dashboard()
