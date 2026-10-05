---
títol: Migrar el heartbeat a cron de Hermes
prioritat: 2
estat: pending
requereix_vistiplau: true
---
# Migrar el heartbeat a cron de Hermes

## Objectiu
Definir els cron jobs de Hermes que substitueixen els 10 mòduls del heartbeat,
en un document de disseny (sense crear-los encara).

## Context
`heartbeat.sh` + `modules/01..10` fan comprovacions periòdiques que Hermes pot fer
com a cron jobs. Cal el mapa mòdul → job abans de crear-los.

## Passos
1. Per a cada mòdul (`01-check-diem` … `10-generate-report`), descriu:
   - què comprova, cada quant, quina acció emprèn, quina notificació envia.
2. Proposa el cron job de Hermes equivalent (schedule, prompt, deliver, skills).
3. Escriu el disseny a `sistema/desenvolupament/MIGRACIO-HEARTBEAT.md` amb una taula.
4. NO creïs els jobs encara (això és decisió de Pol).

## Fitxers
- Create: `sistema/desenvolupament/MIGRACIO-HEARTBEAT.md`
- Read: `sistema/automatitzacio/heartbeat.sh`, `sistema/automatitzacio/modules/*.sh`

## Validació
```bash
cd ~/biblioteca-universal-arion
grep -c '^|' sistema/desenvolupament/MIGRACIO-HEARTBEAT.md   # taula present
```

## Restriccions
- No creïs ni modifiquis cron jobs.
- No esborris cap mòdul.
