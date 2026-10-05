---
títol: Formalitzar el pressupost DIEM i el tall automàtic
prioritat: 4
estat: pending
---
# Formalitzar el pressupost DIEM

## Objectiu
Definir un pressupost DIEM explícit i un tall automàtic documentat i verificable.

## Context
Existeix `sistema/state/diem_stop` (el worker s'atura si hi és) però el llindar no està
formalitzat ni documentat. Cal evitar despeses fora de control.

## Passos
1. Llegeix com es calcula el saldo DIEM (`sistema/automatitzacio/modules/01-check-diem.sh`,
   `sistema/config/diem_costs.conf`).
2. Crea `sistema/config/pressupost.conf` amb paràmetres explícits:
   `DIEM_MINIM_RESERVA`, `DIEM_MAX_DIARI`, `DIEM_MAX_MENSUAL`.
3. Fes que el mòdul de comprovació de DIEM els llegeixi (o documenta com s'hi enllaça)
   i que, en superar el màxim, creï `diem_stop` i notifiqui.
4. Documenta-ho a `OPERACIONS.md`.

## Fitxers
- Create: `sistema/config/pressupost.conf`
- Modify: `sistema/automatitzacio/modules/01-check-diem.sh`
- Modify: `OPERACIONS.md`

## Validació
```bash
cd ~/biblioteca-universal-arion
cat sistema/config/pressupost.conf
bash -n sistema/automatitzacio/modules/01-check-diem.sh && echo "sintaxi OK"
```

## Restriccions
- No activis ni desactivis el worker real; només configura i documenta.
