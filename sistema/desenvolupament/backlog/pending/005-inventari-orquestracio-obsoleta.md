---
títol: Inventariar i arxivar l'orquestració obsoleta
prioritat: 1
estat: pending
---
# Inventariar i arxivar l'orquestració obsoleta

## Objectiu
Identificar tota l'orquestració pròpia que Hermes ja substitueix i moure-la a
`arxiu/orquestracio-obsoleta/` **sense esborrar res encara**.

## Context
El projecte va construir la seva pròpia maquinària (heartbeat, workers, cua,
notificacions, supervisor, brain) quan no hi havia agent general. Ara Hermes +
model orquestrador ho cobreixen. Vegeu `PLA-REFACTOR.md` §1.1 per al mapa.

## Passos
1. Comprova, per a cada fitxer de la llista, **qui el crida**:
   `search_files` per nom a tot el repo, `.github/`, cron i systemd.
2. Genera `arxiu/orquestracio-obsoleta/INVENTARI.md` amb: fitxer, línies, què fa,
   substitut Hermes, i **si algú encara el crida** (sí/no/on).
3. Mou els fitxers **sense referències** a `arxiu/orquestracio-obsoleta/` amb `git mv`.
4. NO esborris cap fitxer. NO toquis `sistema/traduccio/`, `sistema/web/`, `core/`,
   `utils/` ni `obres/` (són domini).

## Llista candidata
`heartbeat.sh`, `modules/00-*.sh`…`11-*.sh`, `worker.sh`, `venice-worker.sh`,
`hermes-worker.sh`, `task-manager.sh`, `notificar.sh`, `notificar-usuari.sh`,
`enviar-informe-discord.sh`, `system-brain.sh`, `millora-continua.sh`,
`monitor-arion.sh`, `worker-status.sh`, `arion-start.sh`, `arion-stop.sh`,
`supervisor-retire-tasks.py`, `hermes_task_executor.py`, `reset-diem.sh`,
`boto_propostes_watchdog.sh`, `consell-editorial.sh`.

## Fitxers
- Create: `arxiu/orquestracio-obsoleta/INVENTARI.md`
- Move: els de la llista sense referències

## Validació
```bash
cd ~/biblioteca-universal-arion
test -f arxiu/orquestracio-obsoleta/INVENTARI.md && echo "OK inventari"
git status --porcelain | grep -c '^R' || true
```

## Restriccions
- Només `git mv`. Cap esborrada. Cap canvi al domini.
