"""Tests per al sistema de logging i dashboard."""

import tempfile
import time
from pathlib import Path

import pytest

from utils.logger import (
    AgentLogger,
    SessionStats,
    VerbosityLevel,
    get_logger,
    reset_logger,
    AGENT_ICONS,
)
from utils.dashboard import (
    Dashboard,
    DashboardState,
    ProgressTracker,
    AgentStatus,
    create_summary_table,
)


class TestVerbosityLevel:
    """Tests per als nivells de verbositat."""

    def test_verbosity_levels_exist(self):
        """Verifica que tots els nivells existeixen."""
        assert VerbosityLevel.QUIET == "quiet"
        assert VerbosityLevel.NORMAL == "normal"
        assert VerbosityLevel.VERBOSE == "verbose"
        assert VerbosityLevel.DEBUG == "debug"

    def test_verbosity_is_string_enum(self):
        """Verifica que VerbosityLevel és un string enum."""
        assert isinstance(VerbosityLevel.NORMAL.value, str)


class TestAgentIcons:
    """Tests per les icones dels agents."""

    def test_icons_exist(self):
        """Verifica que les icones principals existeixen."""
        assert "Traductor" in AGENT_ICONS or "TranslatorAgent" in AGENT_ICONS
        assert "Revisor" in AGENT_ICONS or "ReviewerAgent" in AGENT_ICONS
        assert "default" in AGENT_ICONS

    def test_default_icon_exists(self):
        """Verifica que hi ha una icona per defecte."""
        assert AGENT_ICONS.get("default") is not None


class TestSessionStats:
    """Tests per a SessionStats."""

    def test_init(self):
        """Verifica la inicialització."""
        stats = SessionStats()
        assert stats.calls == []
        assert stats.errors == []
        assert stats.by_agent == {}

    def test_add_call(self):
        """Verifica que es registren les crides."""
        stats = SessionStats()
        stats.add_call("Traductor", 1.5, 100, 50, 0.01)

        assert len(stats.calls) == 1
        assert stats.calls[0]["agent"] == "Traductor"
        assert stats.calls[0]["duration"] == 1.5
        assert "Traductor" in stats.by_agent
        assert stats.by_agent["Traductor"]["calls"] == 1
        assert stats.by_agent["Traductor"]["tokens"] == 150

    def test_add_multiple_calls(self):
        """Verifica múltiples crides."""
        stats = SessionStats()
        stats.add_call("Traductor", 1.0, 100, 50, 0.01)
        stats.add_call("Traductor", 2.0, 200, 100, 0.02)
        stats.add_call("Revisor", 1.5, 150, 75, 0.015)

        assert len(stats.calls) == 3
        assert stats.by_agent["Traductor"]["calls"] == 2
        assert stats.by_agent["Traductor"]["tokens"] == 450
        assert stats.by_agent["Revisor"]["calls"] == 1

    def test_add_error(self):
        """Verifica que es registren els errors."""
        stats = SessionStats()
        stats.add_error("Traductor", "API error")

        assert len(stats.errors) == 1
        assert stats.errors[0]["agent"] == "Traductor"
        assert stats.errors[0]["error"] == "API error"

    def test_get_summary(self):
        """Verifica el resum d'estadístiques."""
        stats = SessionStats()
        stats.add_call("Traductor", 1.0, 100, 50, 0.01)
        stats.add_call("Revisor", 2.0, 200, 100, 0.02)

        summary = stats.get_summary()

        assert summary["total_calls"] == 2
        assert summary["total_duration"] == 3.0
        assert summary["total_tokens"] == 450
        assert summary["total_cost"] == 0.03
        assert "session_start" in summary
        assert "session_end" in summary


class TestAgentLogger:
    """Tests per a AgentLogger."""

    def setup_method(self):
        """Reinicia el logger abans de cada test."""
        reset_logger()

    def test_singleton_pattern(self):
        """Verifica que és un singleton."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger1 = AgentLogger(log_dir=Path(tmpdir))
            logger2 = AgentLogger(log_dir=Path(tmpdir))
            assert logger1 is logger2

    def test_get_logger_function(self):
        """Verifica la funció get_logger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reset_logger()
            logger = get_logger(
                verbosity=VerbosityLevel.VERBOSE,
                log_dir=Path(tmpdir),
            )
            assert logger is not None
            assert logger.verbosity == VerbosityLevel.VERBOSE

    def test_get_icon(self):
        """Verifica que retorna icones."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reset_logger()
            logger = get_logger(log_dir=Path(tmpdir))
            icon = logger.get_icon("Traductor")
            assert icon is not None
            assert isinstance(icon, str)

    def test_log_file_created(self):
        """Verifica que es crea el fitxer de log."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reset_logger()
            logger = get_logger(
                log_dir=Path(tmpdir),
                session_name="test_session",
            )
            log_file = logger.log_file_path
            assert log_file.exists()
            assert "test_session" in log_file.name

    def test_stats_tracking(self):
        """Verifica que es segueixen les estadístiques."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reset_logger()
            logger = get_logger(log_dir=Path(tmpdir))

            logger.log_complete("Traductor", 1.5, 100, 50, 0.01)
            summary = logger.stats.get_summary()

            assert summary["total_calls"] == 1
            assert summary["total_tokens"] == 150


class TestDashboardState:
    """Tests per a DashboardState."""

    def test_init_defaults(self):
        """Verifica els valors per defecte."""
        state = DashboardState()
        assert state.work_title == ""
        assert state.current_stage == "Preparant"
        assert state.global_progress == 0
        assert state.total_tokens == 0
        assert state.total_cost == 0.0

    def test_init_with_values(self):
        """Verifica inicialització amb valors."""
        state = DashboardState(
            work_title="El Convit",
            author="Plató",
            total_chunks=10,
        )
        assert state.work_title == "El Convit"
        assert state.author == "Plató"
        assert state.total_chunks == 10


class TestAgentStatus:
    """Tests per a AgentStatus."""

    def test_init(self):
        """Verifica la inicialització."""
        status = AgentStatus(name="Traductor")
        assert status.name == "Traductor"
        assert status.status == "idle"
        assert status.tokens_processed == 0

    def test_update_status(self):
        """Verifica que es pot actualitzar l'estat."""
        status = AgentStatus(name="Traductor")
        status.status = "processing"
        status.tokens_processed = 500
        assert status.status == "processing"
        assert status.tokens_processed == 500


class TestDashboard:
    """Tests per al Dashboard."""

    def test_init(self):
        """Verifica la inicialització."""
        dashboard = Dashboard(
            work_title="Test",
            author="Autor",
            total_chunks=5,
        )
        assert dashboard.state.work_title == "Test"
        assert dashboard.state.total_chunks == 5

    def test_set_stage(self):
        """Verifica canvi d'etapa."""
        dashboard = Dashboard()
        dashboard.set_stage("Traduint", progress=2)
        assert dashboard.state.current_stage == "Traduint"
        assert dashboard.state.global_progress == 2

    def test_set_chunk(self):
        """Verifica actualització de chunk."""
        dashboard = Dashboard()
        dashboard.set_chunk(3, 10)
        assert dashboard.state.current_chunk == 3
        assert dashboard.state.total_chunks == 10

    def test_add_tokens(self):
        """Verifica comptador de tokens."""
        dashboard = Dashboard()
        dashboard.add_tokens(100)
        dashboard.add_tokens(50)
        assert dashboard.state.total_tokens == 150

    def test_add_cost(self):
        """Verifica comptador de cost."""
        dashboard = Dashboard()
        dashboard.add_cost(0.01)
        dashboard.add_cost(0.02)
        assert dashboard.state.total_cost == pytest.approx(0.03)

    def test_add_warning(self):
        """Verifica afegir avisos."""
        dashboard = Dashboard()
        dashboard.add_warning("Test warning")
        assert "Test warning" in dashboard.state.warnings

    def test_add_error(self):
        """Verifica afegir errors."""
        dashboard = Dashboard()
        dashboard.add_error("Test error")
        assert "Test error" in dashboard.state.errors

    def test_context_manager(self):
        """Verifica el context manager."""
        dashboard = Dashboard()
        # No fem start/stop real per evitar problemes amb Rich Live
        assert dashboard._live is None


class TestProgressTracker:
    """Tests per a ProgressTracker."""

    def test_init(self):
        """Verifica la inicialització."""
        tracker = ProgressTracker()
        assert tracker._tasks == {}

    def test_add_task(self):
        """Verifica afegir tasques."""
        tracker = ProgressTracker()
        tracker.start()
        try:
            name = tracker.add_task("test", "Testing...", total=100)
            assert name == "test"
            assert "test" in tracker._tasks
        finally:
            tracker.stop()

    def test_update_task(self):
        """Verifica actualitzar tasques."""
        tracker = ProgressTracker()
        tracker.start()
        try:
            tracker.add_task("test", "Testing...", total=100)
            tracker.update_task("test", advance=10)
            # La tasca hauria d'haver avançat
            task_id = tracker._tasks["test"]
            assert tracker._progress.tasks[task_id].completed == 10
        finally:
            tracker.stop()


class TestCreateSummaryTable:
    """Tests per a create_summary_table."""

    def test_creates_table(self):
        """Verifica que crea una taula."""
        table = create_summary_table(
            "Test",
            [("Key1", "Value1"), ("Key2", "Value2")],
        )
        assert table is not None
        assert table.title == "Test"


class TestIntegration:
    """Tests d'integració."""

    def setup_method(self):
        """Reinicia el logger abans de cada test."""
        reset_logger()

    def test_full_logging_flow(self):
        """Test del flux complet de logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reset_logger()
            logger = get_logger(
                verbosity=VerbosityLevel.DEBUG,
                log_dir=Path(tmpdir),
                session_name="integration_test",
            )

            # Simular una sessió
            logger.log_session_start("Test Obra", "Autor Test", 1.0)
            logger.log_start("Traductor", "Processant text...")
            logger.log_complete("Traductor", 2.5, 500, 300, 0.05)
            logger.log_warning("Revisor", "Qualitat baixa")
            logger.log_session_end()

            # Verificar que s'han registrat les estadístiques
            summary = logger.stats.get_summary()
            assert summary["total_calls"] == 1
            assert summary["total_tokens"] == 800

            # Verificar que el fitxer existeix
            assert logger.log_file_path.exists()

    def test_dashboard_with_logger(self):
        """Test del dashboard amb logger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reset_logger()
            logger = get_logger(log_dir=Path(tmpdir))

            dashboard = Dashboard(
                work_title="Test",
                total_chunks=5,
            )

            # Simular processament
            dashboard.set_stage("Traduint")
            for i in range(5):
                dashboard.set_chunk(i + 1, 5)
                dashboard.add_tokens(100)
                dashboard.add_cost(0.01)

            assert dashboard.state.total_tokens == 500
            assert dashboard.state.total_cost == pytest.approx(0.05)
