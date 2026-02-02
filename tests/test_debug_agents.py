"""Tests pels agents de debugging.

Tests unitaris i d'integració per BugReproducerAgent, BugFixerAgent
i DebugOrchestrator.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Assegurar mode subscripció per tests
os.environ["CLAUDECODE"] = "1"

from agents.debug.models import BugFix, BugReport, DebugResult
from agents.debug.bug_reproducer import BugReproducerAgent
from agents.debug.bug_fixer import BugFixerAgent
from agents.debug.debug_orchestrator import DebugOrchestrator


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def temp_project_dir():
    """Crea un directori temporal amb estructura de projecte."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Crear estructura bàsica
        (tmpdir / "src").mkdir()
        (tmpdir / "tests").mkdir()

        # Crear un fitxer amb un bug simulat
        buggy_code = '''"""Mòdul amb un bug simulat per testing."""


def divide(a: float, b: float) -> float:
    """Divideix dos nombres.

    Args:
        a: Dividend.
        b: Divisor.

    Returns:
        Resultat de la divisió.
    """
    # BUG: No gestiona divisió per zero
    return a / b


def get_first_element(lst: list) -> any:
    """Retorna el primer element d'una llista.

    Args:
        lst: Llista d'elements.

    Returns:
        Primer element o None si la llista és buida.
    """
    # BUG: No comprova si la llista és buida
    return lst[0]
'''
        (tmpdir / "src" / "calculator.py").write_text(buggy_code)

        yield tmpdir


@pytest.fixture
def sample_bug_report(temp_project_dir):
    """Crea un BugReport de mostra per tests."""
    return BugReport(
        descripcio="La funció divide no gestiona divisió per zero",
        fitxer_afectat=Path("src/calculator.py"),
        funcio_afectada="divide",
        test_code='''import pytest
from src.calculator import divide

def test_divide_by_zero():
    """Verifica que dividir per zero llança excepció."""
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)
''',
        passos_reproduccio=[
            "Importar la funció divide",
            "Cridar divide(10, 0)",
            "Observar que llança ZeroDivisionError sense control",
        ],
        comportament_esperat="Llançar ZeroDivisionError controlat o retornar valor especial",
        comportament_actual="Llança ZeroDivisionError sense control",
        severitat="alta",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS MODELS
# ═══════════════════════════════════════════════════════════════════════════════


class TestBugReportModel:
    """Tests per la classe BugReport."""

    def test_bug_report_creation(self):
        """Verifica que es pot crear un BugReport correctament."""
        report = BugReport(
            descripcio="Test bug",
            fitxer_afectat=Path("test.py"),
            funcio_afectada="test_func",
            test_code="def test(): pass",
            passos_reproduccio=["pas 1", "pas 2"],
            comportament_esperat="correcte",
            comportament_actual="incorrecte",
        )

        assert report.descripcio == "Test bug"
        assert report.fitxer_afectat == Path("test.py")
        assert report.funcio_afectada == "test_func"
        assert report.severitat == "mitjana"  # Default

    def test_bug_report_path_conversion(self):
        """Verifica que els strings es converteixen a Path."""
        report = BugReport(
            descripcio="Test",
            fitxer_afectat="string/path.py",  # type: ignore
            funcio_afectada="func",
            test_code="",
            passos_reproduccio=[],
            comportament_esperat="",
            comportament_actual="",
        )

        assert isinstance(report.fitxer_afectat, Path)

    def test_bug_report_to_dict(self):
        """Verifica la serialització a diccionari."""
        report = BugReport(
            descripcio="Test",
            fitxer_afectat=Path("test.py"),
            funcio_afectada="func",
            test_code="code",
            passos_reproduccio=["pas"],
            comportament_esperat="esperat",
            comportament_actual="actual",
        )

        d = report.to_dict()
        assert d["descripcio"] == "Test"
        assert d["fitxer_afectat"] == "test.py"
        assert "data_creacio" in d


class TestBugFixModel:
    """Tests per la classe BugFix."""

    def test_bug_fix_creation(self, sample_bug_report):
        """Verifica que es pot crear un BugFix correctament."""
        fix = BugFix(
            bug_report=sample_bug_report,
            fitxer_modificat=Path("test.py"),
            diff="- old\n+ new",
            codi_original="old",
            codi_nou="new",
            explicacio="Canvi explicat",
            test_passa=True,
            intents=1,
        )

        assert fix.test_passa is True
        assert fix.intents == 1
        assert fix.exit is True

    def test_bug_fix_exit_property(self, sample_bug_report):
        """Verifica la propietat exit."""
        fix_ok = BugFix(
            bug_report=sample_bug_report,
            fitxer_modificat=Path("test.py"),
            diff="",
            codi_original="",
            codi_nou="",
            explicacio="",
            test_passa=True,
        )
        assert fix_ok.exit is True

        fix_fail = BugFix(
            bug_report=sample_bug_report,
            fitxer_modificat=Path("test.py"),
            diff="",
            codi_original="",
            codi_nou="",
            explicacio="",
            test_passa=False,
        )
        assert fix_fail.exit is False


class TestDebugResultModel:
    """Tests per la classe DebugResult."""

    def test_debug_result_dry_run(self, sample_bug_report):
        """Verifica el resultat en mode dry-run."""
        result = DebugResult(
            bug_report=sample_bug_report,
            dry_run=True,
            temps_total=1.5,
        )

        assert result.exit is True  # Dry-run amb report és èxit
        assert result.dry_run is True
        assert "dry-run" in result.resum().lower()

    def test_debug_result_resum(self, sample_bug_report):
        """Verifica la generació del resum."""
        result = DebugResult(
            bug_report=sample_bug_report,
            temps_total=2.0,
        )

        resum = result.resum()
        assert "divide" in resum
        assert "calculator.py" in resum


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS BUG REPRODUCER AGENT
# ═══════════════════════════════════════════════════════════════════════════════


class TestBugReproducerAgent:
    """Tests per BugReproducerAgent."""

    def test_parse_response_valid(self, temp_project_dir):
        """Verifica el parsing d'una resposta vàlida."""
        agent = BugReproducerAgent(base_dir=temp_project_dir)

        response = """
<fitxer_afectat>src/calculator.py</fitxer_afectat>
<funcio>divide</funcio>
<severitat>alta</severitat>
<test>
import pytest
def test_bug():
    assert False, "Bug demostrat"
</test>
<passos>
1. Importar mòdul
2. Cridar funció
3. Veure error
</passos>
<esperat>No hauria de fallar</esperat>
<actual>Falla</actual>
<context>Info extra</context>
"""
        parsed = agent._parse_response(response)

        assert parsed["fitxer_afectat"] == "src/calculator.py"
        assert parsed["funcio"] == "divide"
        assert parsed["severitat"] == "alta"
        assert "def test_bug" in parsed["test"]
        assert len(parsed["passos"]) == 3
        assert parsed["esperat"] == "No hauria de fallar"

    def test_validate_test_syntax_valid(self, temp_project_dir):
        """Verifica validació de sintaxi Python vàlida."""
        agent = BugReproducerAgent(base_dir=temp_project_dir)

        valid_code = """
import pytest

def test_example():
    assert True
"""
        assert agent._validate_test_syntax(valid_code) is True

    def test_validate_test_syntax_invalid(self, temp_project_dir):
        """Verifica detecció de sintaxi invàlida."""
        agent = BugReproducerAgent(base_dir=temp_project_dir)

        invalid_code = """
def test_broken(
    assert True  # Missing closing parenthesis
"""
        assert agent._validate_test_syntax(invalid_code) is False

    def test_read_source_files(self, temp_project_dir):
        """Verifica la lectura de fitxers font."""
        agent = BugReproducerAgent(base_dir=temp_project_dir)

        content = agent._read_source_files(["src/calculator.py"])

        assert "calculator.py" in content
        assert "def divide" in content

    def test_read_source_files_missing(self, temp_project_dir):
        """Verifica el comportament amb fitxers inexistents."""
        agent = BugReproducerAgent(base_dir=temp_project_dir)

        content = agent._read_source_files(["nonexistent.py"])

        assert "[Cap fitxer llegit]" in content or "nonexistent" not in content


class TestBugReproducerAgentIntegration:
    """Tests d'integració per BugReproducerAgent (requereixen Claude)."""

    @pytest.mark.skip(reason="Test d'integració - requereix Claude CLI")
    def test_reproduce_real_bug(self, temp_project_dir):
        """Test d'integració real amb Claude."""
        agent = BugReproducerAgent(base_dir=temp_project_dir)

        report = agent.reproduce(
            descripcio="La funció divide no gestiona divisió per zero",
            fitxers_context=["src/calculator.py"],
        )

        assert report.fitxer_afectat == Path("src/calculator.py")
        assert "divide" in report.funcio_afectada.lower() or "divide" in report.test_code


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS BUG FIXER AGENT
# ═══════════════════════════════════════════════════════════════════════════════


class TestBugFixerAgent:
    """Tests per BugFixerAgent."""

    def test_parse_response_valid(self, temp_project_dir):
        """Verifica el parsing d'una resposta vàlida."""
        agent = BugFixerAgent(base_dir=temp_project_dir)

        response = """
<analisi>El problema és que no es comprova si b és zero</analisi>
<fitxer>src/calculator.py</fitxer>
<linia_inici>10</linia_inici>
<linia_fi>12</linia_fi>
<codi_original>
return a / b
</codi_original>
<codi_nou>
if b == 0:
    raise ValueError("No es pot dividir per zero")
return a / b
</codi_nou>
<explicacio>Afegit control per divisió per zero</explicacio>
"""
        parsed = agent._parse_response(response)

        assert parsed["fitxer"] == "src/calculator.py"
        assert "return a / b" in parsed["codi_original"]
        assert "if b == 0" in parsed["codi_nou"]
        assert "control" in parsed["explicacio"].lower()

    def test_generate_diff(self, temp_project_dir):
        """Verifica la generació de diffs."""
        agent = BugFixerAgent(base_dir=temp_project_dir)

        original = "def func():\n    return a / b\n"
        nou = "def func():\n    if b == 0:\n        raise ValueError()\n    return a / b\n"

        diff = agent._generate_diff(original, nou, "test.py")

        assert "---" in diff
        assert "+++" in diff
        assert "+if b == 0" in diff or "if b == 0" in diff

    def test_run_test_passing(self, temp_project_dir):
        """Verifica l'execució d'un test que passa."""
        agent = BugFixerAgent(base_dir=temp_project_dir)

        # Crear test que passa
        test_code = """
def test_always_passes():
    assert True
"""
        test_file = temp_project_dir / "tests" / "test_pass.py"
        test_file.write_text(test_code)

        passa, output = agent._run_test(test_file)

        assert passa is True
        assert "passed" in output.lower() or "1 passed" in output

    def test_run_test_failing(self, temp_project_dir):
        """Verifica l'execució d'un test que falla."""
        agent = BugFixerAgent(base_dir=temp_project_dir)

        # Crear test que falla
        test_code = """
def test_always_fails():
    assert False, "Aquest test ha de fallar"
"""
        test_file = temp_project_dir / "tests" / "test_fail.py"
        test_file.write_text(test_code)

        passa, output = agent._run_test(test_file)

        assert passa is False
        assert "failed" in output.lower()

    def test_apply_and_revert_fix(self, temp_project_dir):
        """Verifica l'aplicació i reversió de canvis."""
        agent = BugFixerAgent(base_dir=temp_project_dir)

        # Crear fitxer de prova
        test_file = temp_project_dir / "test_apply.py"
        original_content = "x = 1\ny = 2\nz = x + y"
        test_file.write_text(original_content)

        # Aplicar canvi
        success, msg = agent._apply_fix(
            test_file,
            "y = 2",
            "y = 3",
        )

        assert success is True
        assert "y = 3" in test_file.read_text()

        # Revertir
        reverted = agent._revert_fix(test_file)
        assert reverted is True
        assert test_file.read_text() == original_content


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DEBUG ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════


class TestDebugOrchestrator:
    """Tests per DebugOrchestrator."""

    def test_orchestrator_initialization(self, temp_project_dir):
        """Verifica la inicialització de l'orquestrador."""
        orchestrator = DebugOrchestrator(base_dir=temp_project_dir)

        assert orchestrator.reproducer is not None
        assert orchestrator.fixer is not None
        assert orchestrator.base_dir == temp_project_dir

    def test_orchestrator_verbose_mode(self, temp_project_dir):
        """Verifica el mode verbose."""
        orchestrator = DebugOrchestrator(
            base_dir=temp_project_dir,
            verbose=True,
        )

        assert orchestrator.verbose is True


class TestDebugOrchestratorIntegration:
    """Tests d'integració per DebugOrchestrator."""

    @pytest.mark.skip(reason="Test d'integració - requereix Claude CLI")
    def test_full_debug_flow_dry_run(self, temp_project_dir):
        """Test del flux complet en mode dry-run."""
        orchestrator = DebugOrchestrator(
            base_dir=temp_project_dir,
            verbose=True,
        )

        result = orchestrator.debug(
            descripcio="La funció divide no gestiona divisió per zero",
            fitxers_context=["src/calculator.py"],
            dry_run=True,
        )

        assert result.bug_report is not None
        assert result.dry_run is True
        assert result.bug_fix is None

    @pytest.mark.skip(reason="Test d'integració - requereix Claude CLI")
    def test_full_debug_flow_with_fix(self, temp_project_dir):
        """Test del flux complet amb fix."""
        orchestrator = DebugOrchestrator(
            base_dir=temp_project_dir,
            verbose=True,
        )

        result = orchestrator.debug(
            descripcio="La funció get_first_element no comprova llistes buides",
            fitxers_context=["src/calculator.py"],
            dry_run=False,
        )

        assert result.bug_report is not None
        assert result.bug_fix is not None
        # El fix pot o no passar depenent de la qualitat de la resposta


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS AMB MOCKS
# ═══════════════════════════════════════════════════════════════════════════════


class TestWithMocks:
    """Tests amb mocks per evitar crides reals a Claude."""

    def test_reproducer_with_mocked_process(self, temp_project_dir):
        """Test del reproducer amb process mockejat."""
        agent = BugReproducerAgent(base_dir=temp_project_dir)

        # Mockear la resposta del process
        mock_response = MagicMock()
        mock_response.content = """
<fitxer_afectat>src/calculator.py</fitxer_afectat>
<funcio>divide</funcio>
<severitat>alta</severitat>
<test>
import pytest
def test_divide_zero():
    from src.calculator import divide
    with pytest.raises(ZeroDivisionError):
        divide(1, 0)
</test>
<passos>
1. Importar
2. Cridar
</passos>
<esperat>Excepció controlada</esperat>
<actual>Excepció no controlada</actual>
"""

        with patch.object(agent, "process", return_value=mock_response):
            report = agent.reproduce(
                descripcio="Bug divisió per zero",
                fitxers_context=["src/calculator.py"],
                guardar_test=False,
            )

            assert report.fitxer_afectat == Path("src/calculator.py")
            assert report.funcio_afectada == "divide"
            assert "def test_divide_zero" in report.test_code

    def test_fixer_with_mocked_process(self, temp_project_dir, sample_bug_report):
        """Test del fixer amb process mockejat."""
        agent = BugFixerAgent(base_dir=temp_project_dir, max_intents=1)

        # Mockear la resposta del process
        mock_response = MagicMock()
        mock_response.content = """
<analisi>El problema és que no es comprova b == 0</analisi>
<fitxer>src/calculator.py</fitxer>
<codi_original>return a / b</codi_original>
<codi_nou>if b == 0:
    raise ValueError("Divisió per zero")
return a / b</codi_nou>
<explicacio>Afegit control</explicacio>
"""

        # Mockear també _run_test per simular que el test falla inicialment
        with patch.object(agent, "process", return_value=mock_response), \
             patch.object(agent, "_run_test", return_value=(False, "AssertionError")):
            # No aplicar canvis reals
            fix = agent.fix(
                bug_report=sample_bug_report,
                aplicar_canvis=False,
            )

            assert fix.codi_original == "return a / b"
            assert "if b == 0" in fix.codi_nou


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
