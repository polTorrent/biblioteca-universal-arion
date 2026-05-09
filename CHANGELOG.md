# Changelog

## [2.0.0] — 2026-05-09

### Refactorització completa del sistema

#### Heartbeat modular (abans: monòlit 400+ línies)
- **NOU**: `heartbeat.sh` ara és un orchestrador de ~70 línies
- **NOU**: 10 mòduls independents a `sistema/automatitzacio/modules/`:
  - `01-check-diem.sh` — Comprovació DIEM amb aturada automàtica
  - `02-check-worker.sh` — Monitoratge worker + auto-restart
  - `03-check-failed.sh` — Recuperació intel·ligent de fallides (regen_count, total_failures)
  - `04-check-needs-fix.sh` — Detecció .needs_fix amb creació de tasques
  - `05-check-supervision.sh` — Traduccions sense validar
  - `06-check-translations.sh` — Obres pendents de traducció via obra-queue.json
  - `07-check-web-sync.sh` — Sincronització web
  - `08-check-maintenance.sh` — Manteniment setmanal + rotació logs
  - `09-audit-catalog.sh` — Auditoria catàleg (mode consolidació)
  - `10-generate-report.sh` — Report + notificació Discord
- **NOU**: `common.sh` — Funcions compartides (log, log_json, count_*, add_task, task_exists)
- **NOU**: Logging estructurat JSON lines a `sistema/logs/heartbeat.jsonl`

#### Worker unificat (abans: venice-worker.sh + hermes-worker.sh separats)
- **NOU**: `worker.sh` amb 3 modes: `venice`, `hermes`, `hybrid` (per defecte)
- **NOU**: Circuit breaker PER MODEL (no global) — si model falla 3 vegades, canvia a fallback
- **NOU**: Watchdog cada 5 minuts → `sistema/state/worker_heartbeat.json`
- **NOU**: Graceful shutdown amb trap SIGTERM/SIGINT (retorna running a pending)
- **NOU**: Selector de models dinàmic segons `models.conf` + gènere
- **NOU**: Auto-commit granular (un commit per tasca exitosa)

#### Task Manager Python (abans: task-manager.sh bash)
- **NOU**: `sistema/scripts/task_manager.py` amb deduplicació per hash SHA256
- **NOU**: Prioritats (1=urgent, 5=normal, 9=baixa)
- **NOU**: Dependències entre tasques (depends_on)
- **NOU**: Recovery intel·ligent amb regen_count i total_failures
- **NOU**: CLI completa: add, next, stats, recover, move, retry

#### Notificacions unificades (abans: 4 scripts separats)
- **NOU**: `sistema/automatitzacio/notificar.sh` amb 4 nivells de severitat
- **NOU**: Rate limiting per severitat (CRITICAL sempre passa)
- **NOU**: Fallback Discord → Hermes → log local

#### Scripts Python (abans: lògica inline al heartbeat)
- **NOU**: `check_translations.py` — Analitza obra-queue.json
- **NOU**: `check_supervision.py` — Busca traduccions sense validar
- **NOU**: `update_queue_status.py` — Actualitza estat al catàleg

#### Tests
- **NOU**: `sistema/tests/test_arion.sh` — Suite bàsica (46/48 pass)
- Tests d'estructura, sintaxi bash/python, dedup hash, codi mort

#### Neteja
- **ELIMINAT**: 19,343 línies de codi mort (.tmp files, scripts obsolets)
- **ELIMINAT**: `cron-informe-diari.sh`, `deploy.sh`, `detectar-incompletes-v2.sh`, etc.
- **ELIMINAT**: `serve.sh`, `worker-watchdog.sh`, `worker-with-dashboard.sh`, `heartbeat.sh.backup`
- **MOGUT**: 5 tasques irrecoverables de pending/ a failed/
- **ELIMINAT**: `worker.lock` orfe

#### Documentació
- **NOU**: `OPERACIONS.md` — Manual d'operacions completes
- **NOU**: `CLAUDE.md` — Context del projecte per agents AI
- **NOU**: Dashboard HTML a `docs/index.html`

---

## [1.x] — 2026-04 a 2026-05

### Sistema original
- Heartbeat monolític (400+ línies)
- Workers separats (venice + hermes)
- Notificacions duplicades (4 scripts)
- Task manager en bash
- Cap test
- Lògica Python inline al heartbeat
