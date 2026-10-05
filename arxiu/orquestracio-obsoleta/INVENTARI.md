# Inventari de l'orquestració obsoleta

> **Data:** 2026-10-05 · **Tasca:** 005-inventari-orquestracio-obsoleta · **Referència:** `PLA-REFACTOR.md` §1.1

Llista de l'orquestració pròpia de `sistema/automatitzacio/` que Hermes substitueix.
Res no s'ha esborrat: els fitxers **sense cap cridador** s'han mogut aquí amb `git mv`;
la resta continua al seu lloc fins que es desconnectin els cridadors.

## Metodologia

Per a cada fitxer s'ha cercat el nom (`git grep` + `grep -r`) a tot el repo (inclòs
`.github/`), al `crontab` de l'usuari, a `~/.config/systemd/user/` i a les definicions
de jobs de Hermes (`~/.hermes/cron/jobs.json`). Criteri de «cridat»:

- Compta: codi (`.sh`, `.py`), tests, crontab, systemd, jobs de Hermes (actius o pausats),
  i documentació operativa que el presenta com a ordre a executar (`OPERACIONS.md`).
- No compta: mencions descriptives a `PLA-REFACTOR.md`/`CHANGELOG.md`, el backlog de
  desenvolupament, còpies `.bak` a `scripts/`, ni sortides històriques de `~/.hermes/cron/output/`.

Estat de l'entorn: `crontab` sense cap entrada d'Arion; l'únic servei systemd
(`claude-worker.service`) apunta a `scripts/claude-worker.sh` (fora d'aquesta llista);
`.github/workflows/build.yml` no fa referència a `sistema/automatitzacio/`.
Jobs de Hermes pausats que encara referencien scripts: *Arion Supervisor*
(`heartbeat.sh`, `millora-continua.sh`, `start-worker.sh`, `launch-worker.sh`) i
*arion-supervisio-worker* (`worker.sh`).

## Inventari

| Fitxer | Línies | Què fa | Substitut Hermes | Algú el crida? | Acció |
|--------|-------:|--------|------------------|----------------|-------|
| `heartbeat.sh` | 118 | Orquestrador modular v6 (crida els mòduls 01–10 i `system-brain.sh`) | Cron de Hermes | **Sí**: `arion-start.sh`, `arion-stop.sh`, `sistema/tests/test_arion.sh`, job Hermes pausat *Arion Supervisor* | Es queda |
| `modules/00-update-queue.sh` | 42 | Actualitza `obra-queue.json` i fix-structure | Cron de Hermes | **No** (`heartbeat.sh` no el crida; el test només itera 01–10) | **Mogut** → `modules/00-update-queue.sh` |
| `modules/01-check-diem.sh` | 39 | Comprova saldo DIEM | Cron de Hermes | **Sí**: `heartbeat.sh` | Es queda |
| `modules/02-check-worker.sh` | 49 | Estat del worker + auto-restart | Cron de Hermes | **Sí**: `heartbeat.sh` | Es queda |
| `modules/03-check-failed.sh` | 83 | Recupera tasques fallides | Cron de Hermes | **Sí**: `heartbeat.sh` | Es queda |
| `modules/04-check-needs-fix.sh` | 54 | Detecta `.needs_fix` i crea tasques | Cron de Hermes | **Sí**: `heartbeat.sh` | Es queda |
| `modules/05-check-supervision.sh` | 33 | Traduccions sense validar | Cron de Hermes | **Sí**: `heartbeat.sh` | Es queda |
| `modules/06-check-translations.sh` | 88 | Obres pendents de traducció | Cron de Hermes | **Sí**: `heartbeat.sh` | Es queda |
| `modules/07-check-web-sync.sh` | 34 | Sincronització web | Cron de Hermes | **Sí**: `heartbeat.sh` | Es queda |
| `modules/08-check-maintenance.sh` | 30 | Manteniment setmanal + rotació de logs | Cron de Hermes | **Sí**: `heartbeat.sh` | Es queda |
| `modules/09-audit-catalog.sh` | 37 | Auditoria del catàleg | Cron de Hermes | **Sí**: `heartbeat.sh`, `millora-continua.sh` | Es queda |
| `modules/10-generate-report.sh` | 68 | Genera report i notifica | Cron de Hermes + lliurament natiu | **Sí**: `heartbeat.sh` | Es queda |
| `modules/11-shutdown-report.sh` | 164 | Informe d'aturada per esgotament DIEM | Cron de Hermes + lliurament natiu | **Sí**: `worker.sh` | Es queda |
| `worker.sh` | 620 | Worker unificat (venice/hermes/hybrid) | Skill `biblioteca-arion-worker` | **Sí**: `arion-start.sh`, `arion-stop.sh`, `heartbeat.sh`, `launch-worker.sh`, `start-worker.sh`, `venice-worker.sh`, `monitor-arion.sh`*, `modules/01`,`02`, `sistema/web/dashboard_server.py`, `test_arion.sh`, job Hermes pausat | Es queda |
| `venice-worker.sh` | 960 | Worker autònom amb Venice AI | Skill `biblioteca-arion-worker` | **Sí**: `start-worker.sh` | Es queda |
| `hermes-worker.sh` | 247 | Worker nocturn amb `delegate_task` de Hermes | Agent Hermes natiu | **No** (només mencions a `CHANGELOG.md`/`PLA-REFACTOR.md`) | **Mogut** |
| `task-manager.sh` | 323 | Cua de tasques (add/list/cancel/status) | Cua nativa de Hermes | **Sí**: `heartbeat.sh`, mòduls 01–10, `system-brain.sh`, `millora-continua.sh`, `consell-editorial.sh` | Es queda |
| `notificar.sh` | 153 | Notificacions unificades | Lliurament natiu Discord/Telegram | **Sí**: `arion-start.sh`, `arion-stop.sh`, `modules/11`, `venice-worker.sh`, `test_arion.sh` | Es queda |
| `notificar-usuari.sh` | 100 | Notificació a un usuari de Discord | Lliurament natiu | **Sí**: `notificar.sh` | Es queda |
| `enviar-informe-discord.sh` | 82 | Informe manual a Discord | Lliurament natiu | **Sí**: `notificar.sh`, `venice-worker.sh` | Es queda |
| `system-brain.sh` | 963 | Bucle de decisió / auto-millora | Raonament de l'agent + skills | **Sí**: `heartbeat.sh` (fa `source`) | Es queda |
| `millora-continua.sh` | 486 | Millora contínua d'obres validades | Raonament de l'agent + skills | **Sí**: `system-brain.sh`, `supervisor-retire-tasks.py`*, job Hermes pausat | Es queda |
| `monitor-arion.sh` | 131 | Monitoratge cada 15 min amb alertes | Cron de Hermes | **No** (cap cron/systemd/job actual; només sortides antigues de Hermes) | **Mogut** |
| `worker-status.sh` | 74 | Estat ràpid del worker | Cron + `status.sh` | **Sí**: `start-worker.sh` | Es queda |
| `arion-start.sh` | 108 | Arrencada del sistema | Cron de Hermes | **Sí**: documentat a `OPERACIONS.md` com a ordre d'arrencada | Es queda (conservador) |
| `arion-stop.sh` | 62 | Aturada (graceful) del sistema | Cron de Hermes | **Sí**: documentat a `OPERACIONS.md` com a ordre d'aturada | Es queda (conservador) |
| `supervisor-retire-tasks.py` | 51 | Retira tasques a `failed_permanent` | Agent Hermes | **No** | **Mogut** |
| `hermes_task_executor.py` | 132 | Pont cap a Hermes | Natiu (no cal pont) | **Sí**: `worker.sh`, `hermes-worker.sh`* | Es queda |
| `reset-diem.sh` | 41 | Reinici després del reset de DIEM | Cron de Hermes | **Sí**: `arion-start.sh`, `worker.sh` | Es queda |
| `boto_propostes_watchdog.sh` | 44 | Regenera el botó de propostes | Cron de Hermes | **No** (la capçalera diu «heartbeat + cron cada 10 min», però ja no hi és a cap dels dos) | **Mogut** |
| `consell-editorial.sh` | 140 | Agent del Consell Editorial | Agent Hermes | **Sí**: `system-brain.sh` | Es queda |

\* Cridador que també s'ha arxivat (o és candidat), però que comptava en el moment de l'anàlisi.

## Resum

- **Moguts (5):** `hermes-worker.sh`, `monitor-arion.sh`, `supervisor-retire-tasks.py`,
  `boto_propostes_watchdog.sh`, `modules/00-update-queue.sh` (~515 línies).
- **Es queden (26):** formen una xarxa de crides entre si arrelada a `heartbeat.sh`,
  `worker.sh`, `arion-start/stop.sh`, `test_arion.sh` i dos jobs de Hermes pausats.

## Següents passos (fora d'aquesta tasca)

1. Esborrar els jobs de Hermes pausats *Arion Supervisor* i *arion-supervisio-worker*.
2. Substituir `arion-start/stop.sh` a `OPERACIONS.md` per l'equivalent Hermes.
3. Adaptar `sistema/tests/test_arion.sh` perquè no exigeixi `heartbeat.sh`/`worker.sh`/`notificar.sh`.
4. Llavors arxivar en bloc l'arbre arrelat a `heartbeat.sh` i `worker.sh`.
