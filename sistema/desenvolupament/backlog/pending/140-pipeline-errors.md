---
títol: El pipeline no ha d'escriure errors com a traducció
prioritat: 1
estat: pending
---
# El pipeline no ha d'escriure errors com a traducció

## Objectiu
Quan el Claude CLI falla (p. ex. límit de subscripció `429`), `traduir_pipeline.py`
NO ha d'escriure el text de l'error a `traduccio.md` com si fos la traducció.

## Context
Validant el camí de subscripció (2026-10-05), el CLI va tornar
`429 "You've hit your session limit"` i el pipeline va escriure el JSON de l'error
dins `traduccio.md`, i va imprimir "✅ TRADUCCIÓ PIPELINE V2 COMPLETADA".
Això **corrompria una obra real de manera silenciosa**.

## Passos
1. A `sistema/traduccio/agents/base_agent.py::_call_claude_cli`, comprova també el JSON
   de resposta: si `is_error == true` o `api_error_status` és present (p.ex. 429),
   llança `RuntimeError` encara que `returncode == 0`.
2. A `sistema/traduccio/traduir_pipeline.py`: si el pipeline falla, **no escriguis**
   `traduccio.md`; surt amb codi ≠ 0 i un missatge clar ("límit de subscripció;
   reintenta després del reset").
3. Rebutja qualsevol traducció que contingui `[ERROR:` o el JSON de l'error.
4. Afegeix un test a `sistema/tests/` que verifiqui que un error no genera `traduccio.md`.

## Fitxers
- Modify: `sistema/traduccio/agents/base_agent.py`, `sistema/traduccio/traduir_pipeline.py`
- Create: `sistema/tests/test_pipeline_errors.py`

## Validació
```bash
cd ~/biblioteca-universal-arion
python3 -m pytest sistema/tests/test_pipeline_errors.py -q
```

## Restriccions
- No canviïs la lògica del camí feliç; només el maneig d'errors.
