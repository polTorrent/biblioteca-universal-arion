---
títol: Punt d'entrada únic (Makefile) en comptes de symlinks fràgils
prioritat: 5
estat: pending
---
# Punt d'entrada únic

## Objectiu
Substituir els symlinks de `scripts/` per un `Makefile` a l'arrel amb comandes clares.

## Context
`scripts/` és ple de symlinks cap a `sistema/`, cosa que trenca fàcilment (vegeu la
tasca 010). Un `Makefile` és explícit, versionable i no es trenca.

## Passos
1. Crea un `Makefile` a l'arrel amb objectius:
   `heartbeat`, `worker`, `status`, `test`, `build`, `dev` (→ dev-worker),
   `probe` (→ quota-probe), `clean`.
2. Cada objectiu crida el script real de `sistema/` amb la ruta correcta.
3. Afegeix un objectiu `help` per defecte que llisti les comandes.
4. Documenta'l breument a `README.md`.

## Fitxers
- Create: `Makefile`
- Modify: `README.md`

## Validació
```bash
cd ~/biblioteca-universal-arion
make help
make probe
```

## Restriccions
- No esborris `scripts/` en aquesta tasca (només afegeix el Makefile).
- Els objectius no han de fer push ni tocar dades.
