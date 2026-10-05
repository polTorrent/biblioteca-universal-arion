---
títol: Treure del control de versions la brutícia rastrejada
prioritat: 2
estat: pending
---
# Treure del control de versions la brutícia rastrejada

## Objectiu
Deixar de rastrejar `_tmp_hicks.txt` (3 MB) i els fitxers `*.bak.20260226` de `scripts/`.

## Context
Hi ha fitxers que no haurien de ser al repo: `_tmp_hicks.txt` a l'arrel i
`scripts/heartbeat.sh.bak.20260226`, `scripts/improve-openclaw.sh.bak.20260226`.

## Passos
1. Assegura't que `.gitignore` ja cobreix aquests patrons (tasca 020).
2. Treu-los del control de versions **sense esborrar-los del disc**:
   ```bash
   git rm --cached _tmp_hicks.txt
   git rm --cached scripts/heartbeat.sh.bak.20260226 scripts/improve-openclaw.sh.bak.20260226
   ```
3. Mou els `.bak` a una carpeta `arxiu/` local si vols conservar-los (opcional).

## Fitxers
- `_tmp_hicks.txt`
- `scripts/heartbeat.sh.bak.20260226`
- `scripts/improve-openclaw.sh.bak.20260226`

## Validació
```bash
cd ~/biblioteca-universal-arion
git ls-files | grep -E '_tmp_hicks|\.bak\.20260226' || echo "OK: cap brutícia rastrejada"
```

## Restriccions
- Usa `git rm --cached`, MAI `git rm` sense `--cached` (no esborris del disc).
