---
títol: Pre-commit local (ruff, shellcheck, detecció de secrets)
prioritat: 4
estat: pending
---
# Pre-commit local

## Objectiu
Aturar canvis defectuosos o amb secrets abans del commit.

## Context
Els canvis autònoms i humans entren directament. Un pre-commit lleuger redueix
regressions i el risc de filtrar claus.

## Passos
1. Crea `.pre-commit-config.yaml` amb:
   - `ruff` (lint + format de Python)
   - `shellcheck` per a `*.sh`
   - `detect-secrets` (o `gitleaks`) per a claus
   - `check-yaml`, `end-of-file-fixer`, `trailing-whitespace`
2. Afegeix al `pyproject.toml` la secció `[tool.ruff]` amb configuració bàsica
   (línia 100, target py311) si no existeix.
3. Documenta a `CONTRIBUTING.md` com instal·lar i executar: `pre-commit install`.

## Fitxers
- Create: `.pre-commit-config.yaml`
- Modify: `pyproject.toml`
- Modify: `CONTRIBUTING.md`

## Validació
```bash
cd ~/biblioteca-universal-arion
python3 -c "import yaml; yaml.safe_load(open('.pre-commit-config.yaml')); print('OK')"
```

## Restriccions
- No instal·lis el hook globalment ni facis commit automàtic de tot el repo.
