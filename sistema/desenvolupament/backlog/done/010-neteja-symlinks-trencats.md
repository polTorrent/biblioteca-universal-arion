---
títol: Netejar els symlinks trencats de scripts/
prioritat: 1
estat: pending
---
# Netejar els symlinks trencats de scripts/

## Objectiu
Eliminar els 6 enllaços simbòlics trencats de `scripts/` que apunten a fitxers inexistents.

## Context
`scripts/` conté symlinks cap a `sistema/`, però 6 d'ells apunten a destinacions que ja
no existeixen. Provoca errors silenciosos i confusió.

## Passos
1. Localitza els symlinks trencats: `find scripts -xtype l`.
2. Per a cada un, comprova si la destinació real existeix en un altre lloc
   (`search_files` o `find`). Si existeix, reapunta'l; si no, elimina el symlink.
3. Documenta la decisió a `OPERACIONS.md` (secció breu "Punts d'entrada").

## Fitxers
- `scripts/` (symlinks trencats: `deploy.sh`, `serve.sh`, `worker-watchdog.sh`,
  `claude-worker-mini.sh`, `improve-openclaw.sh`, `informe_detallat.py`)

## Validació
```bash
cd ~/biblioteca-universal-arion
find scripts -xtype l          # ha de sortir buit
```

## Restriccions
- No esborris cap fitxer real, només symlinks trencats.
