---
títol: Tests de la cua de tasques (task_manager.py)
prioritat: 3
estat: pending
---
# Tests de la cua de tasques

## Objectiu
Cobrir amb tests la lògica crítica de `sistema/scripts/task_manager.py`.

## Context
La cua de tasques és el cor del sistema autònom i no té tests unitaris. Un bug aquí
atura tota la producció.

## Passos
1. Llegeix `sistema/scripts/task_manager.py` i identifica les funcions clau
   (`add`, `next`, `stats`, `recover`, `retry`, dedup per hash).
2. Crea `sistema/tests/test_task_manager.py` amb `pytest`, usant un directori temporal
   (`tmp_path`) com a cua, sense tocar `sistema/tasks/` real.
3. Cobreix com a mínim: afegir, deduplicació, prioritat, recuperació i reintent.
4. Executa els tests i assegura't que passen.

## Fitxers
- Create: `sistema/tests/test_task_manager.py`
- Read: `sistema/scripts/task_manager.py`

## Validació
```bash
cd ~/biblioteca-universal-arion
python3 -m pytest sistema/tests/test_task_manager.py -q
```

## Restriccions
- No modifiquis `sistema/tasks/` real; fes servir directoris temporals.
