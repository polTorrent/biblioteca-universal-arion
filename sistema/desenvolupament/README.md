# Desenvolupament autònom — Arion

Sistema que aprofita la **quota lliure de la subscripció Claude Pro** per fer
avançar el codi de la Biblioteca Universal Arion sense intervenció humana.

## Components

| Fitxer | Funció |
|--------|--------|
| `quota-probe.py` | Sonda: comprova si la subscripció té quota lliure (`FREE`/`LIMIT`/`ERROR`) |
| `dev-worker.sh` | Bucle autònom: resol tasques del backlog amb Claude Code |
| `status.sh` | Estat: quota, backlog, commits `[auto-dev]` |
| `enqueue.sh` | Afegeix tasques al backlog |
| `claude-dev-guard.sh` | Hook que bloqueja ordres destructives |
| `claude-dev-settings.json` | Settings de Claude Code per al worker |
| `PROMPT.md` | Instruccions permanents afegides a cada tasca |
| `backlog/` | Cua de tasques (`pending/ running/ done/ failed/`) |

## Flux

```
cron (20 min)
   └─ dev-worker.sh
        ├─ quota-probe.py → FREE?
        │     sí  → agafa tasca de backlog/pending/
        │           → claude -p (branca auto/dev, guard actiu)
        │           → commit [auto-dev] → backlog/done/
        │           → repeteix (fins a DEV_MAX_TASKS)
        │     no  → s'atura (LIMIT) o reintenta més tard (ERROR)
        └─ s'atura si: quota esgotada · backlog buit · 3 errors seguits
```

**Mai fa push. Mai toca `main`.** Els canvis queden a la branca `auto/dev` perquè una
persona els revisi i els fusioni:

```bash
cd ~/biblioteca-universal-arion
git log --oneline main..auto/dev      # veure els canvis
git diff main..auto/dev               # revisar
git checkout main && git merge auto/dev
```

## Ús

```bash
cd ~/biblioteca-universal-arion/sistema/desenvolupament

python3 quota-probe.py            # comprova quota ara
bash status.sh                    # estat complet
bash dev-worker.sh --dry-run      # veure què faria (sense executar Claude)
bash dev-worker.sh                # una passada real
bash dev-worker.sh --once         # només una tasca

bash enqueue.sh --new "El meu títol"   # crear plantilla de tasca
bash enqueue.sh /ruta/tasca.md 3       # encuar amb prioritat 3
bash enqueue.sh --list                 # llistar backlog
```

## Variables d'entorn

| Variable | Defecte | Descripció |
|----------|---------|------------|
| `DEV_MODEL` | `opus` | Model de Claude Code |
| `DEV_MAX_TASKS` | `6` | Màxim de tasques per passada |
| `DEV_MAX_TURNS` | `40` | Màxim de torns per tasca |
| `DEV_MAX_TASK_SECS` | `1800` | Timeout per tasca (30 min) |
| `DEV_MAX_CONSEC_FAILS` | `3` | Errors seguits abans d'aturar |
| `DEV_COOLDOWN` | `20` | Segons entre tasques |
| `DEV_BRANCH` | `auto/dev` | Branca de treball |
| `QUOTA_PROBE_MODEL` | `haiku` | Model de la sonda |

## Programació

Un job de Hermes cron executa `dev-worker.sh` cada 20 minuts. El worker s'autolimita
(pany, quota, màxim de tasques), així que encavalcar-se és impossible.

```bash
hermes cron create --name "Arion Dev" --schedule "*/20 * * * *" \
  --prompt "Executa bash ~/biblioteca-universal-arion/sistema/desenvolupament/dev-worker.sh i reporta només si hi ha hagut canvis o errors."
```

## Seguretat

- Guard `PreToolUse` bloqueja: `git push`, `--force`, `reset --hard`, `rm -rf /`, `sudo`,
  `curl|sh`, escriptura a `.env`, claus (`sk-ant-`, `ghp_`).
- `permissions.deny` impedeix llegir `.env` i fitxers de tokens.
- Treball sempre en branca; `main` intocable.
- Notificació a Discord via `sistema/automatitzacio/notificar.sh` en cas de límit o errors.
