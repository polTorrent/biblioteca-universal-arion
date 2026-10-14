"""Tests de la detecció i neteja de metadades filtrades dins les traduccions.

Cobreix el format REAL que apareix als fitxers: les tanques **mutilades**
``'`'json`` (apòstrof + accent greu + apòstrof), que ni el fix de 2026-10-11 ni
els patrons ```` ```json ```` reconeixien. També fixa que el sanejat no toqui
contingut legítim (blocs ```català, diàlegs amb cometes, prosa normal).
"""

import json
import sys
from pathlib import Path

import pytest

_TESTS = Path(__file__).resolve()
_SISTEMA = _TESTS.parents[1]          # <arrel>/sistema
_ROOT = _TESTS.parents[2]             # <arrel>
sys.path.insert(0, str(_SISTEMA))
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_SISTEMA / "traduccio"))

from agents.v2.pipeline_v2 import PipelineV2  # noqa: E402
from agents.v2.sanititzacio import (  # noqa: E402
    es_linia_tanca,
    netejar_i_validar,
    sembla_metadades,
    te_bloc_metadades,
    netejar_metadades,
)

BT = "`" * 3

# Blocs filtrats reals (extrets de .chunks_traduïts.json de les obres afectades).
BLOC_MUTILAT_BUIT = "'`'json\n'`'"
BLOC_MUTILAT_FRAGMENT = (
    "'`'json\n"
    '        "v. 23: «de quina manera li paga Jàson» recupera el to irònic"\n'
    "'`'"
)
BLOC_MUTILAT_LLARG = (
    "'`'json\n"
    ',"a notes.md.",\n'
    '        "El text grec de 3.4 («μήποτε») és obscur; la solució és una interpretació.",\n'
    '        "El grec conté una lliçó dubtosa; he seguit el sentit general."\n'
    "'`'"
)


# ── 1. DETECCIÓ DE LÍNIES DE TANCA ───────────────────────────────────────────

def test_linia_tanca_accepta_el_format_mutilat():
    assert es_linia_tanca("'`'json") is True
    assert es_linia_tanca("'`'") is True
    assert es_linia_tanca(BT) is True
    assert es_linia_tanca(BT + "json") is True
    assert es_linia_tanca("~~~") is True
    assert es_linia_tanca("  '`'json  ") is True


def test_linia_tanca_no_confon_cometes_ni_llenguatges():
    assert es_linia_tanca("") is False
    assert es_linia_tanca("'") is False
    assert es_linia_tanca("'\"") is False       # diàleg alemany/anglès
    assert es_linia_tanca('"') is False
    assert es_linia_tanca(BT + "català") is False  # bloc de codi legítim


# ── 2. NETEJA DELS BLOCS FILTRATS ────────────────────────────────────────────

@pytest.mark.parametrize("bloc", [BLOC_MUTILAT_BUIT, BLOC_MUTILAT_FRAGMENT, BLOC_MUTILAT_LLARG])
def test_neteja_bloc_mutilat_sencer(bloc):
    """Un contingut que és només el bloc filtrat queda sense res aprofitable."""
    net, motiu = netejar_i_validar(bloc)
    assert net.strip() == ""
    assert motiu is not None
    assert "'`'" not in net


def test_neteja_bloc_mutilat_incrustat():
    """El bloc s'elimina i es conserva la prosa del voltant."""
    text = f"Traducció bona del fragment.\n\n{BLOC_MUTILAT_LLARG}\n\nMés traducció bona."
    net, motiu = netejar_i_validar(text)
    assert "'`'" not in net
    assert "Traducció bona del fragment." in net
    assert "Més traducció bona." in net
    assert motiu is None


def test_recupera_text_de_json_amb_traduccio():
    """Si el bloc conté el text traduït, s'aprofita en lloc de llençar-lo."""
    text = '{\n  "traduccio": "El text de debò.",\n  "canvis_aplicats": ["canvi"]\n}'
    net, motiu = netejar_i_validar(text)
    assert net == "El text de debò."
    assert motiu is None

    embolcallat = BT + 'json\n{"traduccio": "Text embolcallat."}\n' + BT
    net2, motiu2 = netejar_i_validar(embolcallat)
    assert net2 == "Text embolcallat."
    assert motiu2 is None


def test_descarta_array_de_canvis():
    text = BT + 'json\n["canvi 1", "canvi 2"]\n' + BT
    net, motiu = netejar_i_validar(text)
    assert net.strip() == ""
    assert motiu is not None


def test_detecta_filtrat_sense_tanques():
    """Fragments d'array filtrats sense tanques (cas real de del-sublim)."""
    text = (
        "## Capítol 15\n\n"
        '"Substituit \'sota l\'impuls de\' per \'mogut per\'",\n'
        '"Reordenat \'el de la dels discursos\' per \'el dels discursos\'",\n'
        '"Canviat \'el més aplicat a portar a la tragèdia\'",\n'
        '"Eliminat l\'ús excessiu de guions llargues"\n'
    )
    assert sembla_metadades(text) is True
    _, motiu = netejar_i_validar(text)
    assert motiu is not None


# ── 3. EL SANEJAT NO TOCA CONTINGUT LEGÍTIM ─────────────────────────────────

def test_no_toca_blocs_de_codi_legitims():
    text = "ÍNDEX.\n\n" + BT + "català\nPÀG.\n  PREFACI    vii\n" + BT + "\n\nFi de l'índex."
    assert netejar_metadades(text) == text
    assert te_bloc_metadades(text) is False
    _, motiu = netejar_i_validar(text)
    assert motiu is None


def test_no_toca_prosa_ni_dialegs():
    casos = [
        "El gat dorm sobre la catifa. «Ei!», va dir.",
        '"Dariuxka, què fem per dinar?"\n\n—No ho sé.',
        "**[9.1]** Això és una nota crítica amb [claudàtors] i 'apòstrofs'.",
        "—Vós, el vostre ajudant, sou moralment molt inferiors a nosaltres.",
    ]
    for text in casos:
        assert netejar_metadades(text) == text
        _, motiu = netejar_i_validar(text)
        assert motiu is None, f"fals positiu sobre: {text!r}"


def test_descarta_buit_i_marques_error():
    assert netejar_i_validar("")[1] is not None
    assert netejar_i_validar("   \n  ")[1] is not None
    _, motiu = netejar_i_validar("Traducció\n[ERROR: Claude CLI ha fallat]")
    assert motiu is not None
    _, motiu2 = netejar_i_validar('{"is_error": true}')
    assert motiu2 is not None


# ── 4. REGRESSIÓ SOBRE DADES REALS DEL DISC ─────────────────────────────────

def _chunks_files() -> list[Path]:
    return sorted((_ROOT / "obres").glob("**/.chunks_traduïts.json"))


def test_cap_chunk_real_rete_bloc_filtrat():
    """Cap chunk desat pot retenir un bloc de metadades després del sanejat."""
    files = _chunks_files()
    if not files:
        pytest.skip("no hi ha chunks al disc")
    revisats = 0
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for cid, txt in data.items():
            if not isinstance(txt, str):
                continue
            revisats += 1
            net, motiu = netejar_i_validar(txt)
            assert "'`'json" not in net, f"{path.parent.name}:{cid} reté el bloc mutilat"
            assert BT not in net, f"{path.parent.name}:{cid} reté una tanca de codi"
            if motiu is None:
                assert sembla_metadades(net) is False, (
                    f"{path.parent.name}:{cid} acceptat però encara sembla metadades"
                )
    assert revisats > 0


def test_detecta_traduccions_publicades_amb_filtrat():
    """Les traduccions publicades amb filtrat conegut han de ser detectables."""
    conegudes = [
        _ROOT / "obres/assaig/pseudo-longi/del-sublim/traduccio.md",
        _ROOT / "obres/oriental/kalidasa/kumarasambhava-el-naixement-del-deu-de-la-guerra/traduccio.md",
    ]
    trobades = 0
    for path in conegudes:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if sembla_metadades(text) or te_bloc_metadades(text):
            trobades += 1
    assert trobades > 0, "el detector no veu cap filtrat on n'hi ha"


# ── 5. GUARDES DEL PIPELINE (desar/carregar chunks) ─────────────────────────

class _EstatFals:
    """Estat mínim per provar els mètodes de desar/carregar chunks."""

    def __init__(self, obra_dir: Path) -> None:
        self.obra_dir = obra_dir


@pytest.fixture()
def pipeline_fals(tmp_path):
    p = PipelineV2.__new__(PipelineV2)
    p.logger = None
    p.estat = _EstatFals(tmp_path)
    return p


def test_guardar_chunk_rebutja_metadades(pipeline_fals, tmp_path):
    assert pipeline_fals._guardar_traduccio_chunk("chunk_1", BLOC_MUTILAT_BUIT) is False
    assert pipeline_fals._guardar_traduccio_chunk("chunk_2", "") is False
    # No s'ha desat cap valor, però el fitxer pot existir per l'esborrat de claus
    fitxer = tmp_path / ".chunks_traduïts.json"
    if fitxer.exists():
        assert json.loads(fitxer.read_text(encoding="utf-8")) == {}

    assert pipeline_fals._guardar_traduccio_chunk("chunk_3", "Text bo de la traducció.") is True
    assert pipeline_fals._carregar_traduccio_chunk("chunk_3") == "Text bo de la traducció."
    assert pipeline_fals._carregar_traduccio_chunk("chunk_1") is None


def test_carregar_chunk_neteja_i_descarta(pipeline_fals, tmp_path):
    fitxer = tmp_path / ".chunks_traduïts.json"
    fitxer.write_text(
        json.dumps(
            {
                "chunk_1": BLOC_MUTILAT_FRAGMENT,
                "chunk_2": 'Prosa bona.\n\n' + BLOC_MUTILAT_LLARG,
                "chunk_3": "[ERROR: Claude CLI ha fallat]",
                "chunk_4": "Text recuperat de debò.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    assert pipeline_fals._carregar_traduccio_chunk("chunk_1") is None
    assert pipeline_fals._carregar_traduccio_chunk("chunk_3") is None
    recuperat = pipeline_fals._carregar_traduccio_chunk("chunk_2")
    assert recuperat is not None and "'`'" not in recuperat
    assert pipeline_fals._carregar_traduccio_chunk("chunk_4") == "Text recuperat de debò."


# ── 6. EMPREMES DE FRAGMENTACIÓ A L'ESTAT DEL PIPELINE ─────────────────────

def test_empremtes_chunks_es_guarden_i_es_llegeixen(tmp_path):
    from core import EstatPipeline

    estat = EstatPipeline(tmp_path, "Autor", "Obra", "llatí")
    ids = ["chunk_1", "chunk_2"]
    empremtes = ["aaaa11112222", "bbbb33334444"]
    estat.registrar_chunks(ids, empremtes)
    assert estat.empremtes_chunks() == empremtes

    # Represa: les empremtes han de sobreviure a un carregar/guardar
    recarregat = EstatPipeline(tmp_path, "Autor", "Obra", "llatí")
    assert recarregat.carregar() is True
    assert recarregat.empremtes_chunks() == empremtes

    recarregat.reiniciar_chunks(ids, ["cccc55556666"])
    assert recarregat.empremtes_chunks() == ["cccc55556666"]
    assert recarregat.chunks_completats == 0
