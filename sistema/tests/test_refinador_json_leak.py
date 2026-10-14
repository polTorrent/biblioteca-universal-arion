"""Tests per al bug del refinador que filtrava JSON intern dins la traducció.

Context (2026-10-10): el refinador retornava, en alguns casos, el JSON de
«canvis aplicats» (un array de strings) en lloc del text refinat.

Atenció: el fix de 2026-10-11 va suposar que el bloc sortia amb tanques ```json,
però el format REAL als fitxers porta les tanques mutilades (``'`'json``). Aquí
es fixen les dues bandes amb tots dos formats (vegeu també
`test_sanititzacio_metadades.py`):

  1. `AgentRefinador._extreure_traduccio` no ha de retornar mai JSON/blocs.
  2. `PipelineV2._netejar_json_traduccio` ha d'eliminar el bloc filtrat.
"""

import json
import sys
from pathlib import Path

import pytest

# Afegir sistema/ i sistema/traduccio al path (com fa traduir_pipeline.py)
_TESTS = Path(__file__).resolve()
_SISTEMA = _TESTS.parents[1]                 # <arrel>/sistema
_ROOT = _TESTS.parents[2]                    # <arrel>
sys.path.insert(0, str(_SISTEMA))
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_SISTEMA / "traduccio"))

from agents.v2.pipeline_v2 import PipelineV2          # noqa: E402
from agents.v2.refinador_iteratiu import AgentRefinador  # noqa: E402

BT = "`" * 3  # tanca de codi markdown

# Bloc filtrat tal com el va produir el refinador (array de strings).
BLOC_FILTRAT = (
    BT + "json\n"
    '"«original» → «traducció»",\n'
    '"«altre fragment» → «canvi aplicat»"\n'
    + BT
)


@pytest.fixture(scope="module")
def refinador() -> AgentRefinador:
    return AgentRefinador()


# ── 1. NETEJA AL PIPELINE ────────────────────────────────────────────────────

def test_neteja_bloc_sencer():
    """Un chunk que és NOMÉS el bloc filtrat queda buit."""
    net = PipelineV2._netejar_json_traduccio(None, BLOC_FILTRAT)
    assert BT not in net
    assert "json" not in net
    assert net.strip() == ""


def test_neteja_bloc_incrustat():
    """El bloc incrustat s'elimina i es conserva el text del voltant."""
    text = f"Abans del bloc.\n\n{BLOC_FILTRAT}\n\nDesprés del bloc."
    net = PipelineV2._netejar_json_traduccio(None, text)
    assert BT not in net
    assert "Abans del bloc." in net
    assert "Després del bloc." in net


def test_neteja_no_toca_text_net():
    """Una traducció normal no es modifica."""
    text = "**[1.3]** Estimadíssim amic, quan parlem d'algú expert en literatura..."
    assert PipelineV2._netejar_json_traduccio(None, text) == text


# ── 2. REFINADOR: MAI RETORNAR JSON COM A TEXT ───────────────────────────────

def test_sembla_json(refinador):
    assert refinador._sembla_json(BLOC_FILTRAT) is True
    assert refinador._sembla_json('["a", "b"]') is True
    assert refinador._sembla_json('{"traduccio_refinada": "x"}') is True
    # No és JSON: numeració de secció i text literari
    assert refinador._sembla_json("[1.3] Estimadíssim amic, quan parlem...") is False
    assert refinador._sembla_json("Text traduït normal i llarg " * 5) is False


def test_extreure_descarta_bloc_sencer(refinador):
    """Resposta = només el bloc JSON → es manté la traducció prèvia."""
    assert refinador._extreure_traduccio(BLOC_FILTRAT, "TRADUCCIÓ PRÈVIA") == "TRADUCCIÓ PRÈVIA"


def test_extreure_descarta_array_json(refinador):
    assert refinador._extreure_traduccio('["a", "b", "c"]', "PRÈVIA") == "PRÈVIA"


def test_extreure_treu_bloc_mixt(refinador):
    """Text + bloc filtrat → es retorna el text sense el bloc."""
    text = f"Traducció vàlida prou llarga per superar el llindar de longitud.\n{BLOC_FILTRAT}"
    out = refinador._extreure_traduccio(text, "PRÈVIA")
    assert BT not in out
    assert out.startswith("Traducció vàlida")


def test_extreure_conserva_text_pla(refinador):
    """Una traducció en text pla es conserva."""
    text = "Aquesta és una traducció en text pla, sense cap JSON, i prou llarga per ser acceptada."
    assert refinador._extreure_traduccio(text, "PRÈVIA") == text


# ── 3. REGRESSIÓ SOBRE CHUNKS REALS (si existeixen al disc) ──────────────────

def test_neteja_chunks_reals_medea():
    """Cap chunk guardat de les obres afectades ha de retenir el bloc filtrat."""
    obres = [
        _ROOT / "obres/teatre/euripides/medea/.chunks_traduïts.json",
        _ROOT / "obres/assaig/pseudo-longi/del-sublim/.chunks_traduïts.json",
    ]
    for path in obres:
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for cid, txt in data.items():
            if not isinstance(txt, str):
                continue
            net = PipelineV2._netejar_json_traduccio(None, txt)
            assert BT not in net, f"{path.name}:{cid} encara conté un bloc de codi"
            assert "'`'json" not in net, f"{path.name}:{cid} encara conté el bloc mutilat"


# ── 4. FORMAT REAL: TANQUES MUTILADES ``'`'json`` ─────────��─────────────────

TANCA_MUTILADA = "'`'json"
BLOC_MUTILAT = TANCA_MUTILADA + "\n'`'"
BLOC_MUTILAT_FRAGMENT = (
    TANCA_MUTILADA
    + "\n"
    + '        "v. 23: «de quina manera li paga Jàson» recupera el to irònic"\n'
    + "'`'"
)


def test_neteja_bloc_mutilat():
    """El bloc amb tanques mutilades (format real) també s'elimina."""
    assert PipelineV2._netejar_json_traduccio(None, BLOC_MUTILAT).strip() == ""
    assert PipelineV2._netejar_json_traduccio(None, BLOC_MUTILAT_FRAGMENT).strip() == ""

    mixt = f"Traducció real del fragment.\n\n{BLOC_MUTILAT_FRAGMENT}\n\nMés text."
    net = PipelineV2._netejar_json_traduccio(None, mixt)
    assert TANCA_MUTILADA not in net
    assert "Traducció real del fragment." in net
    assert "Més text." in net


def test_sembla_json_detecta_tanques_mutilades(refinador):
    assert refinador._sembla_json(BLOC_MUTILAT) is True
    assert refinador._sembla_json(BLOC_MUTILAT_FRAGMENT) is True


def test_extreure_descarta_bloc_mutilat(refinador):
    assert refinador._extreure_traduccio(BLOC_MUTILAT_FRAGMENT, "PRÈVIA") == "PRÈVIA"
