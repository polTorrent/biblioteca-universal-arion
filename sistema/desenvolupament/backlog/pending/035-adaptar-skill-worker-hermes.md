---
títol: Adaptar el skill biblioteca-arion-worker al model Hermes-natiu
prioritat: 2
estat: pending
---
# Adaptar el skill biblioteca-arion-worker

## Objectiu
Reescriure el skill `biblioteca-arion-worker` perquè l'agent Hermes faci la feina
que abans feien els workers bash, sense intermediaris.

## Context
El skill existeix a `~/.hermes/skills/openclaw-imports/biblioteca-arion-worker/` i
encara descriu el flux antic (heartbeat + venice-worker.sh + task_manager). Cal
actualitzar-lo al model nou: Hermes orquestra, el domini s'invoca com a eina.

## Passos
1. Llegeix el skill actual i `PLA-REFACTOR.md` §1.
2. Reescriu la secció d'operativa perquè descrigui:
   - com l'agent executa una traducció (invocant `sistema/traduccio/traduir_pipeline.py`),
   - com comprova qualitat i DIEM,
   - què ja NO cal fer (heartbeat, workers bash).
3. Afegeix un exemple de cron job de Hermes per a la producció de traduccions.
4. Mantén la part de domini (criteris per gènere, models per tipus).

## Fitxers
- Modify: `~/.hermes/skills/openclaw-imports/biblioteca-arion-worker/SKILL.md`

## Validació
```bash
grep -c 'heartbeat' ~/.hermes/skills/openclaw-imports/biblioteca-arion-worker/SKILL.md
# hauria de baixar respecte de l'original
```

## Restriccions
- No toquis altres skills.
- Mantén el frontmatter vàlid (name, description).
