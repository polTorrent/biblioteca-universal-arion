"""
Tests unitaris de sistema/scripts/task_manager.py

Tots els tests fan servir un directori temporal (tmp_path) com a cua;
mai no toquen sistema/tasks/ real.
"""
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "task_manager.py"


@pytest.fixture
def tm(tmp_path, monkeypatch):
    """Carrega task_manager amb TASKS_DIR redirigit a un directori temporal."""
    spec = importlib.util.spec_from_file_location("task_manager_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "TASKS_DIR", tmp_path / "cua")
    return mod


def llegir(path: Path) -> dict:
    return json.loads(path.read_text())


# ── Hash ─────────────────────────────────────────────────────────────────────

def test_hash_normalitza_majuscules_i_espais(tm):
    assert tm.task_hash("traduir", "  Hola Món ") == tm.task_hash("traduir", "hola món")


def test_hash_depen_del_tipus(tm):
    assert tm.task_hash("traduir", "x") != tm.task_hash("revisar", "x")


# ── Afegir ───────────────────────────────────────────────────────────────────

def test_add_crea_tasca_pending(tm):
    path = tm.add_task("traduir", "Traduir Sèneca", priority=2,
                       model="claude", depends_on=["abc"], metadata={"k": "v"})
    assert path is not None
    assert path.parent == tm.TASKS_DIR / "pending"
    d = llegir(path)
    assert d["type"] == "traduir"
    assert d["instruction"] == "Traduir Sèneca"
    assert d["priority"] == 2
    assert d["retries"] == 0
    assert d["model"] == "claude"
    assert d["depends_on"] == ["abc"]
    assert d["metadata"] == {"k": "v"}
    assert d["_hash"] == tm.task_hash("traduir", "Traduir Sèneca")
    assert d["id"].startswith("traduir-")
    assert path.name == f"{d['id']}.json"


def test_add_camps_opcionals_absents(tm):
    d = llegir(tm.add_task("traduir", "x"))
    assert d["priority"] == 5
    for camp in ("model", "depends_on", "metadata"):
        assert camp not in d


# ── Deduplicació ─────────────────────────────────────────────────────────────

def test_dedup_mateixa_tasca_pending(tm):
    assert tm.add_task("traduir", "Obra A") is not None
    assert tm.add_task("traduir", "  obra a ") is None
    assert tm.stats()["pending"] == 1


def test_dedup_tasca_running(tm):
    p = tm.add_task("traduir", "Obra A")
    tm.move_task(p, "running")
    assert tm.add_task("traduir", "Obra A") is None


def test_no_dedup_si_done(tm):
    p = tm.add_task("traduir", "Obra A")
    tm.move_task(p, "done")
    assert tm.add_task("traduir", "Obra A") is not None


def test_no_dedup_tipus_diferent(tm):
    assert tm.add_task("traduir", "Obra A") is not None
    assert tm.add_task("revisar", "Obra A") is not None


def test_find_by_hash_ignora_json_corrupte(tm):
    (tm.task_dir("pending") / "trencat.json").write_text("{no és json")
    assert tm.add_task("traduir", "Obra A") is not None


# ── Prioritat i next ─────────────────────────────────────────────────────────

def test_next_buit(tm):
    assert tm.next_task() is None


def test_next_tria_prioritat_mes_baixa(tm):
    tm.add_task("traduir", "baixa", priority=9)
    urgent = tm.add_task("traduir", "urgent", priority=1)
    tm.add_task("traduir", "normal", priority=5)
    assert tm.next_task() == urgent


def test_next_respecta_dependencies(tm):
    dep = tm.add_task("traduir", "prerequisit", priority=1)
    dep_id = llegir(dep)["id"]
    depenent = tm.add_task("revisar", "despres", priority=1, depends_on=[dep_id])
    altra = tm.add_task("traduir", "independent", priority=5)

    # El prerequisit encara és pending → la depenent no és elegible
    tm.move_task(dep, "running")
    assert tm.next_task() == altra

    # Quan el prerequisit és done, la depenent passa a ser elegible
    tm.move_task(tm.TASKS_DIR / "running" / dep.name, "done")
    assert tm.next_task() == depenent


# ── Moure i estadístiques ────────────────────────────────────────────────────

def test_move_task(tm):
    p = tm.add_task("traduir", "x")
    dest = tm.move_task(p, "running")
    assert not p.exists()
    assert dest.exists() and dest.parent.name == "running"


def test_stats(tm):
    tm.add_task("traduir", "a")
    tm.move_task(tm.add_task("traduir", "b"), "done")
    tm.move_task(tm.add_task("traduir", "c"), "failed")
    assert tm.stats() == {"pending": 1, "running": 0, "done": 1,
                          "failed": 1, "failed_permanent": 0}


# ── Reintent ─────────────────────────────────────────────────────────────────

def test_retry_torna_a_pending(tm):
    p = tm.move_task(tm.add_task("traduir", "x"), "running")
    assert tm.retry_task(p) is True
    nou = tm.TASKS_DIR / "pending" / p.name
    assert nou.exists() and not p.exists()
    assert llegir(nou)["retries"] == 1


def test_retry_excedit_va_a_failed(tm):
    p = tm.move_task(tm.add_task("traduir", "x"), "running")
    d = llegir(p)
    d["retries"] = 2  # el següent reintent arriba a max_retries (3)
    p.write_text(json.dumps(d))
    assert tm.retry_task(p) is False
    assert (tm.TASKS_DIR / "failed" / p.name).exists()
    assert not (tm.TASKS_DIR / "pending" / p.name).exists()


def test_retry_respecta_max_retries_personalitzat(tm):
    p = tm.move_task(tm.add_task("traduir", "x"), "running")
    d = llegir(p)
    d["max_retries"] = 1
    p.write_text(json.dumps(d))
    assert tm.retry_task(p) is False
    assert (tm.TASKS_DIR / "failed" / p.name).exists()


# ── Recuperació ──────────────────────────────────────────────────────────────

def test_recover_torna_a_pending(tm):
    p = tm.add_task("traduir", "x")
    d = llegir(p)
    d["retries"] = 3
    d["total_failures"] = 3
    p.write_text(json.dumps(d))
    tm.move_task(p, "failed")

    assert tm.recover_failed() == 1
    nou = tm.TASKS_DIR / "pending" / p.name
    d = llegir(nou)
    assert d["retries"] == 0
    assert d["regen_count"] == 1
    assert d["recovered"] is True


def test_recover_massa_fallades_va_a_permanent(tm):
    p = tm.add_task("traduir", "x")
    d = llegir(p)
    d["total_failures"] = 9
    p.write_text(json.dumps(d))
    tm.move_task(p, "failed")

    assert tm.recover_failed() == 0
    assert (tm.TASKS_DIR / "failed_permanent" / p.name).exists()
    assert tm.stats()["failed"] == 0


def test_recover_massa_regeneracions_va_a_permanent(tm):
    p = tm.add_task("traduir", "x")
    d = llegir(p)
    d["regen_count"] = 3
    p.write_text(json.dumps(d))
    tm.move_task(p, "failed")

    assert tm.recover_failed() == 0
    assert (tm.TASKS_DIR / "failed_permanent" / p.name).exists()


def test_recover_ignora_json_corrupte(tm):
    (tm.task_dir("failed") / "trencat.json").write_text("{no és json")
    assert tm.recover_failed() == 0
    assert (tm.TASKS_DIR / "failed" / "trencat.json").exists()


def test_no_toca_cua_real(tm, tmp_path):
    assert tm.TASKS_DIR == tmp_path / "cua"
    assert tm.task_dir("pending").is_relative_to(tmp_path)
