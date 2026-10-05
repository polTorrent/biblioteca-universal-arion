---
títol: Guardrails de cost DIEM a la configuració de Hermes
prioritat: 4
estat: pending
requereix_vistiplau: true
---
# Guardrails de cost DIEM

## Objectiu
Definir el pressupost DIEM i els guardrails **a la configuració de Hermes**, no en bash.

## Context
Existeix `sistema/state/diem_stop` (el worker s'atura si hi és) però el llindar no està
formalitzat. Amb Hermes com a orquestrador, el control de cost ha de viure a la config
de Hermes i al routing de models, no en mòduls bash.

## Passos
1. Documenta el saldo DIEM actual i el cost mitjà per traducció.
2. Defineix llindars: reserva mínima, màxim diari, màxim mensual.
3. Proposa com aplicar-los a Hermes (config del provider, skills de routing, un cron
   de comprovació de saldo que aturi la producció si cal).
4. Escriu la proposta a `sistema/desenvolupament/PRESSUPOST-DIEM.md` i afegeix els
   valors a `sistema/config/diem_costs.conf` (o un fitxer nou `pressupost.conf`).

## Fitxers
- Create: `sistema/desenvolupament/PRESSUPOST-DIEM.md`
- Modify: `sistema/config/diem_costs.conf`

## Validació
```bash
cd ~/biblioteca-universal-arion
cat sistema/desenvolupament/PRESSUPOST-DIEM.md | head
```

## Restriccions
- No activis ni desactivis el worker real.
- No posis claus ni credencials a cap fitxer.
