---
títol: Ampliar .gitignore (runtime, temporals, brutícia de Windows)
prioritat: 1
estat: pending
---
# Ampliar .gitignore

## Objectiu
Evitar que fitxers d'estat, temporals i brutícia de Windows tornin a entrar al repo.

## Context
`git status` mostra sovint fitxers d'estat (`sistema/state/*`), logs i fitxers
`*:Zone.Identifier` de Windows. Cal blindar-ho al `.gitignore`.

## Passos
1. Obre `.gitignore`.
2. Afegeix, sota una secció `# Arion runtime & temporals`, com a mínim:
   ```
   _tmp_*
   *.bak
   *.bak.*
   *.orig
   *:Zone.Identifier
   sistema/state/quota_raw.txt
   sistema/desenvolupament/state/
   sistema/desenvolupament/dev-worker.log
   sistema/desenvolupament/backlog/running/
   ```
3. Comprova que els patrons funcionen amb `git check-ignore -v` sobre exemples.

## Fitxers
- `.gitignore`

## Validació
```bash
cd ~/biblioteca-universal-arion
git check-ignore -v _tmp_hicks.txt
git check-ignore -v sistema/desenvolupament/state/quota.json
```

## Restriccions
- No treguis entrades existents del `.gitignore`.
