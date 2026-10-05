---
títol: Actualitzar README i docs a l'estat real (models i arquitectura)
prioritat: 3
estat: pending
---
# Actualitzar README i docs

## Objectiu
Posar `README.md` i `OPERACIONS.md` d'acord amb l'estat real del projecte.

## Context
El `README.md` encara diu "claude-opus-4-7", "deepseek-v3.2", "glm-5" i "~3.5 DIEM",
però `sistema/config/models.conf` ja fa servir `kimi-k2-5`, `llama-3.3-70b` i
`qwen3-235b-a22b-thinking-2507`. Els agents nous queden confosos.

## Passos
1. Llegeix `sistema/config/models.conf` i extreu la taula real de models per tipus.
2. Actualitza la secció "Models i costos" del `README.md` amb els models reals.
3. Actualitza l'arbre d'estructura del `README.md` perquè reflecteixi
   `sistema/desenvolupament/`, `PLA-REFACTOR.md` i la resta.
4. Afegeix a `OPERACIONS.md` una secció "Desenvolupament autònom" que enllaci
   `sistema/desenvolupament/README.md`.

## Fitxers
- Modify: `README.md`
- Modify: `OPERACIONS.md`

## Validació
```bash
cd ~/biblioteca-universal-arion
grep -n "kimi-k2-5" README.md    # ha d'aparèixer
grep -n "deepseek-v3.2\|claude-opus-4-7" README.md || echo "OK: models antics fora"
```

## Restriccions
- Mantén l'estil i l'estructura existents del README.
- No inventis xifres: si un cost no és clar, deixa'l com a "n/d".
