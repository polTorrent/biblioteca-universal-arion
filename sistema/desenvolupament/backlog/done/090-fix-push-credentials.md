---
títol: Restaurar el push a GitHub (PAT de polTorrent)
prioritat: 1
estat: pending
requereix_vistiplau: true
---
# Restaurar el push a GitHub

## Objectiu
Tornar a poder fer `git push origin main` amb el compte correcte (`polTorrent`).

## Context
El push falla: `remote: Permission ... denied to jordivinyalsferre-wq`. El credential
helper està fent servir el token de l'altre compte. El repo és de `polTorrent`.
Hi ha 16 commits locals sense pujar des del 2026-06-05 i la web pública no s'actualitza.

## Per què requereix vistiplau
Toca credencials. **No ho ha de fer un agent sol.** Decisió i execució humanes.

## Passos (per a una persona)
1. Generar un PAT de `polTorrent` amb àmbit `repo` (o reaprofitar `~/.hermes/gh_pol.token`).
2. Configurar el credential helper **scopat al repo**:
   ```bash
   cd ~/biblioteca-universal-arion
   git config --local credential.helper store
   printf 'https://<PAT>@github.com\n' > .git/.git-credentials   # fora del working tree
   git config --local credential.helper "store --file=.git/.git-credentials"
   chmod 600 .git/.git-credentials
   ```
3. Comprovar: `git push --dry-run origin main`.
4. Fer el push real.

## Validació
```bash
cd ~/biblioteca-universal-arion
git push --dry-run origin main && echo "OK"
git log --oneline origin/main..main | wc -l   # ha de ser 0
```

## Restriccions
- MAI desar credencials al working tree ni al repo.
- MAI posar el PAT a `.env` ni a cap fitxer rastrejat.
