---
títol: Integració contínua (GitHub Actions) — lint + tests + build
prioritat: 2
estat: pending
---
# Integració contínua amb GitHub Actions

## Objectiu
Crear un workflow que validi cada push/PR: lint de Python i shell, tests i build de la web.

## Context
No hi ha CI. `sistema/tests/test_arion.sh` passa 46/48. Cal una xarxa de seguretat
automàtica perquè els canvis autònoms no trenquin res.

## Passos
1. Crea `.github/workflows/ci.yml` amb:
   - Trigger: `push` i `pull_request` a `main` i `auto/dev`.
   - Job `lint`: `ruff check .` (instal·la `ruff`) i `shellcheck` sobre `sistema/**/*.sh`
     i `scripts/*.sh` (ignora symlinks trencats).
   - Job `test`: instal·la deps (`pip install -e ".[dev]"`) i executa `pytest -q`
     (o `bash sistema/tests/test_arion.sh`).
   - Job `build`: `python3 scripts/build.py --clean` en un directori temporal.
2. Fes servir `actions/checkout@v4` i `actions/setup-python@v5` (Python 3.11).
3. Si algun pas falla per motius preexistents, marca'l `continue-on-error: true` i
   deixa un comentari `# TODO` explicant-ho (no amaguis fallades noves).

## Fitxers
- Create: `.github/workflows/ci.yml`

## Validació
```bash
python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml')); print('YAML OK')"
```

## Restriccions
- No afegeixis secrets al workflow.
- No facis push.
