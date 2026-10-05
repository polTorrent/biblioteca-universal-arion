---
títol: Arxivar l'orquestració reemplaçada i actualitzar tests
prioritat: 3
estat: pending
---
# Arxivar l'orquestració reemplaçada

## Objectiu
Un cop Hermes substitueix el heartbeat/worker/notificacions, moure els scripts
reemplaçats a l'arxiu i actualitzar els tests que els referencien.

## Context
Continuació de la tasca 005. Ara que es creen els cron jobs de Hermes (015) i es
substitueixen les notificacions (025), es poden retirar els scripts vells.

## Passos
1. Mou a `arxiu/orquestracio-obsoleta/` (amb `git mv`):
   `heartbeat.sh`, `modules/` (tot), `worker.sh`, `venice-worker.sh`, `hermes-worker.sh`,
   `launch-worker.sh`, `start-worker.sh`, `worker-status.sh`, `monitor-arion.sh`,
   `arion-start.sh`, `arion-stop.sh`, `notificar.sh`, `notificar-usuari.sh`,
   `enviar-informe-discord.sh`, `system-brain.sh`, `millora-continua.sh`,
   `task-manager.sh`, `reset-diem.sh`, `boto_propostes_watchdog.sh`,
   `supervisor-retire-tasks.py`, `hermes_task_executor.py`.
2. **NO** arxivis (són domini o utilitats útils): `auditar-cataleg.sh`, `fix-structure.sh`,
   `detectar-incompletes.sh`, `processar-propostes.sh`, `propostes-discord.sh`.
3. Actualitza `sistema/tests/test_arion.sh`: la validació de sintaxi ha d'iterar només
   sobre fitxers existents (que no falli si `modules/` o els scripts ja no hi són).
4. Executa `bash sistema/tests/test_arion.sh` i assegura't que tot passa.

## Fitxers
- Move: els de la llista del pas 1
- Modify: `sistema/tests/test_arion.sh`

## Validació
```bash
cd ~/biblioteca-universal-arion
bash sistema/tests/test_arion.sh 2>&1 | tail -3          # tot ✅
find sistema/automatitzacio -maxdepth 1 -name '*.sh' | wc -l   # molt menys que abans
```

## Restriccions
- No esborris res. No toquis `sistema/traduccio/`, `sistema/web/`, `core/`, `utils/`,
  ni `sistema/desenvolupament/`.
