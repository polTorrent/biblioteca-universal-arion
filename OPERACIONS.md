# 📖 OPERACIONS — Biblioteca Universal Arion

## Arquitectura v6

```
heartbeat.sh (orchestrador)
├── 01-check-diem.sh       → Comprovació saldo DIEM
├── 02-check-worker.sh     → Estat worker + auto-restart
├── 03-check-failed.sh     → Recuperació tasques fallides
├── 04-check-needs-fix.sh  → Obres amb .needs_fix
├── 05-check-supervision.sh→ Traduccions sense validar
├── 06-check-translations.sh→ Obres pendents traducció
├── 07-check-web-sync.sh   → Sincronització web
├── 08-check-maintenance.sh→ Manteniment setmanal
├── 09-audit-catalog.sh    → Auditoria catàleg
└── 10-generate-report.sh  → Report + notificació

worker.sh (unificat)
├── mode=venice  → Venice AI per tot
├── mode=hermes  → Hermes delegate_task per tot
└── mode=hybrid  → Venice=traduccions, Hermes=fix/supervisió (DEFAULT)

task_manager.py (dedup per hash)
├── add     → Afegeix tasca (deduplicada)
├── next    → Següent tasca per prioritat
├── stats   → Estadístiques
├── recover → Recupera fallides
└── retry   → Reintent amb comptador

notificar.sh (unificat)
├── info/warning/error/critical → Nivells de severitat
├── report → Report heartbeat
└── Rate limiting per severitat
```

## Comandes operatives

### Iniciar sistema
```bash
bash ~/biblioteca-universal-arion/sistema/automatitzacio/arion-start.sh
```

### Aturar sistema
```bash
bash ~/biblioteca-universal-arion/sistema/automatitzacio/arion-stop.sh
```

### Executar heartbeat manualment
```bash
bash ~/biblioteca-universal-arion/sistema/automatitzacio/heartbeat.sh
```

### Executar worker manualment
```bash
# Mode hybrid (recomanat)
bash ~/biblioteca-universal-arion/sistema/automatitzacio/worker.sh --mode=hybrid

# Mode Venice només
bash ~/biblioteca-universal-arion/sistema/automatitzacio/worker.sh --mode=venice
```

### Pausar el sistema
```bash
echo "PAUSED_UNTIL=2026-05-10" > ~/biblioteca-universal-arion/PAUSE
```

### Reprendre
```bash
rm ~/biblioteca-universal-arion/PAUSE
```

### Task manager
```bash
cd ~/biblioteca-universal-arion
python3 sistema/scripts/task_manager.py stats
python3 sistema/scripts/task_manager.py add translate "Traduir Plató - Apologia"
python3 sistema/scripts/task_manager.py recover
```

### Notificacions
```bash
source sistema/automatitzacio/notificar.sh
notify_info "Títol" "Missatge informatiu"
notify_critical "EMERGÈNCIA" "Worker aturat"
```

### Tests
```bash
bash ~/biblioteca-universal-arion/sistema/tests/test_arion.sh
```

## Variables crítiques

| Variable | Valor | Fitxer |
|----------|-------|--------|
| MAX_PENDING | 5 | heartbeat.sh |
| MIN_DIEM_RESERVE | 3 | heartbeat.sh, worker.sh |
| MAX_CONSECUTIVE_FAILS | 3 | worker.sh |
| MAX_RUNTIME | 32400s (9h) | worker.sh |
| TASK_TIMEOUT_VENICE | 300s | worker.sh |
| TASK_TIMEOUT_HERMES | 1800s | worker.sh |

## Estat del sistema

- `sistema/state/heartbeat_state.json` — Estat de l'últim heartbeat
- `sistema/state/worker_heartbeat.json` — Watchdog del worker
- `sistema/logs/heartbeat.log` — Log del heartbeat
- `sistema/logs/worker.log` — Log del worker
- `sistema/logs/heartbeat.jsonl` — Log estructurat JSON

L'estat es consulta amb:

- `bash sistema/desenvolupament/status.sh` — quota, backlog i commits del desenvolupament autònom
- **Informe diari de Hermes** — cron de Hermes que lliura l'estat a Discord

El dashboard propi (`sistema/dashboard/`, `sistema/automatitzacio/dashboard.sh`,
`sistema/web/dashboard_server.py`) s'ha retirat i arxivat a `arxiu/orquestracio-obsoleta/`.

## Web

Web **estàtica** generada a `docs/` (no rastrejada al git). La publica
`.github/workflows/build.yml` a la branca `gh-pages` a cada push a `main`.

- Construcció: `python3 sistema/web/build.py --clean`
- Verificació d'enllaços interns: `python3 sistema/web/check_links.py`
- Lògica: `sistema/web/generador/` (`markdown.py`, `loader.py`, `builder.py`)
- Sense backend: l'autenticació (Supabase), els favorits, la gamificació i el
  micromecenatge es van retirar el 2026-10-05 i són a `arxiu/web-interactiva/`.

Detall complet: `sistema/web/README.md`.

## Punts d'entrada

`scripts/` només ha de contenir symlinks vàlids. S'han eliminat 14 symlinks trencats
en total: `deploy.sh`, `serve.sh`, `worker-watchdog.sh`, `claude-worker-mini.sh`,
`improve-openclaw.sh`, `informe_detallat.py`, `dashboard_server.py`, `heartbeat.sh`,
`millora-continua.sh`, `notificar-usuari.sh`, `start-worker.sh`, `system-brain.sh`,
`task-manager.sh` i `worker-status.sh`: les destinacions ja no existeixen a
`sistema/` (són a `arxiu/`).

## Troubleshooting

### Worker no arrenca
1. Comprova lockfile: `rm ~/biblioteca-universal-arion/sistema/tasks/worker.lock`
2. Comprova DIEM: `python3 ~/.hermes/skills/openclaw-imports/venice-ai/scripts/venice.py balance`
3. Comprova logs: `tail -50 ~/biblioteca-universal-arion/sistema/logs/worker.log`

### Tasques no es processen
1. Comprova pending: `ls sistema/tasks/pending/ | wc -l`
2. Comprova running: `ls sistema/tasks/running/ | wc -l`
3. Comprova worker actiu: `pgrep -f worker.sh`

### Massa errors consecutius
1. El worker fa pausa d'emergència de 10 min automàticament
2. Si persisteix, comprova models.conf i saldo DIEM
3. Forçar reinici: `pkill -f worker.sh && bash sistema/automatitzacio/worker.sh --mode=hybrid`

## Desenvolupament autònom

El codi del projecte també avança de manera autònoma amb un worker de
desenvolupament (Claude Code) que resol tasques d'un backlog a la branca `auto/dev`.
Documentació completa: [`sistema/desenvolupament/README.md`](sistema/desenvolupament/README.md).

```bash
bash ~/biblioteca-universal-arion/sistema/desenvolupament/status.sh   # Estat: quota, backlog, commits
```
