"""Tests: un error del Claude CLI mai no s'ha d'escriure com a traducció.

Cas real (2026-10-05): el CLI va tornar 429 "You've hit your session limit" i el
pipeline va escriure el JSON de l'error a traduccio.md.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

_ARREL = Path(__file__).resolve().parents[2]
_TRADUCCIO = _ARREL / "sistema" / "traduccio"
for _p in (_ARREL, _ARREL / "sistema", _TRADUCCIO):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from agents.base_agent import BaseAgent  # noqa: E402
import traduir_pipeline  # noqa: E402

JSON_429 = {
    "type": "result",
    "subtype": "success",
    "is_error": True,
    "api_error_status": 429,
    "result": "You've hit your session limit · resets 3pm",
}


class _AgentProva(BaseAgent):
    system_prompt = "prova"


def _agent_fals():
    """Instància mínima d'agent sense passar pel constructor."""
    agent = object.__new__(_AgentProva)
    agent.config = SimpleNamespace(model="sonnet")
    agent.logger = mock.MagicMock()
    agent.agent_name = "test"
    return agent


# ── base_agent._call_claude_cli ──────────────────────────────────────────────

def test_cli_error_json_amb_returncode_0_llanca_runtimeerror():
    completat = subprocess.CompletedProcess(
        args=[], returncode=0, stdout=json.dumps(JSON_429), stderr=""
    )
    with mock.patch("agents.base_agent.subprocess.run", return_value=completat):
        with pytest.raises(RuntimeError, match="429"):
            BaseAgent._call_claude_cli(_agent_fals(), "prompt", "system")


def test_cli_api_error_status_sense_is_error_llanca_runtimeerror():
    dades = {"type": "result", "api_error_status": 429, "result": "límit"}
    completat = subprocess.CompletedProcess(
        args=[], returncode=0, stdout=json.dumps(dades), stderr=""
    )
    with mock.patch("agents.base_agent.subprocess.run", return_value=completat):
        with pytest.raises(RuntimeError):
            BaseAgent._call_claude_cli(_agent_fals(), "prompt", "system")


def test_cli_resposta_correcta_es_retorna():
    dades = {"type": "result", "is_error": False, "result": "Traducció bona."}
    completat = subprocess.CompletedProcess(
        args=[], returncode=0, stdout=json.dumps(dades), stderr=""
    )
    with mock.patch("agents.base_agent.subprocess.run", return_value=completat):
        assert BaseAgent._call_claude_cli(_agent_fals(), "p", "s") == dades


# ── traduir_pipeline.validar_resultat_pipeline ──────────────────────────────

def _resultat(text, fase="completat", errors=None):
    return SimpleNamespace(
        traduccio_final=text,
        fase=SimpleNamespace(value=fase),
        errors=errors or [],
    )


@pytest.mark.parametrize("text", [
    "",
    "   ",
    "Capítol I\n\n[ERROR: Claude CLI ha fallat]",
    json.dumps(JSON_429),
])
def test_validar_rebutja_errors(text):
    assert traduir_pipeline.validar_resultat_pipeline(_resultat(text)) is not None


def test_validar_rebutja_fase_error():
    r = _resultat("text qualsevol", fase="error", errors=["Error fatal"])
    assert traduir_pipeline.validar_resultat_pipeline(r) is not None


def test_validar_missatge_limit_subscripcio():
    r = _resultat("[ERROR: api_error_status=429 session limit]")
    msg = traduir_pipeline.validar_resultat_pipeline(r)
    assert "límit de subscripció" in msg


def test_validar_accepta_traduccio_correcta():
    r = _resultat("Breu és la vida, llarg l'art.")
    assert traduir_pipeline.validar_resultat_pipeline(r) is None


# ── traduir_pipeline.main: no escriu traduccio.md si hi ha error ─────────────

@pytest.mark.parametrize("resultat", [
    _resultat("[ERROR: Claude CLI ha retornat un error (api_error_status=429)]",
              errors=["Error en chunk 1: 429 session limit"]),
    _resultat("", fase="error", errors=["Error fatal: 429"]),
])
def test_main_no_escriu_traduccio_si_error(tmp_path, monkeypatch, resultat):
    obra = tmp_path / "obra"
    obra.mkdir()
    (obra / "original.md").write_text("## I\n\n" + "Lorem ipsum dolor. " * 60,
                                      encoding="utf-8")

    pipeline_fals = mock.MagicMock()
    pipeline_fals.traduir.return_value = resultat
    monkeypatch.setattr(traduir_pipeline, "PipelineV2",
                        mock.MagicMock(return_value=pipeline_fals))
    monkeypatch.setattr(traduir_pipeline, "ConfiguracioPipelineV2", mock.MagicMock())
    monkeypatch.setattr(sys, "argv", ["traduir_pipeline.py", str(obra)])

    with pytest.raises(SystemExit) as exc:
        traduir_pipeline.main()

    assert exc.value.code != 0
    assert not (obra / "traduccio.md").exists()
