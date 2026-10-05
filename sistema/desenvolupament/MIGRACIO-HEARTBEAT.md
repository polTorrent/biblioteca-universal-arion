# Migració del heartbeat a cron de Hermes — document de disseny

> Tasca 015 del backlog · `PLA-REFACTOR.md` §T2.2.
> **Només disseny.** Cap job no s'ha creat ni modificat: la decisió és de Pol.

## 1. Estat actual (2026-10-05)

- `sistema/automatitzacio/heartbeat.sh` (v6) encadena els mòduls de
  `sistema/automatitzacio/modules/` en fases: 0 (crítiques) → 1 (auditoria i
  recuperació) → 1.5 (web) → 2 (generació de tasques, només si `pending < MAX_PENDING=5`)
  → 3 (manteniment i informe).
- **El heartbeat ja no està planificat enlloc**: no apareix al `crontab` de l'usuari ni
  a `~/.hermes/cron/jobs.json`. Ara mateix només s'executa a mà.
- Jobs de Hermes d'Arion que ja existeixen i que solapen amb mòduls:
  - `07da592c79f7` **Arion — informe diari** (`0 9 * * *`, skill `biblioteca-arion-worker`)
    → cobreix gran part de `10-generate-report` i la lectura del DIEM de `01`.
  - `929b6f1f1391` **Arion — auditoria setmanal del catàleg** (`0 10 * * 0`)
    → cobreix `09-audit-catalog` (però sense `--fix`, només informe).
  - `83a6d0c91c27` **Arion Dev** (`*/30`) → no relacionat amb el heartbeat.
- Els mòduls depenen de la cua pròpia (`sistema/tasks/*`, `task-manager.sh`) i del
  `worker.sh`, tots dos **obsolets**. Per tant, la migració no consisteix a «cridar
  el mòdul des d'un cron», sinó a decidir què fa l'agent de Hermes directament.

## 2. Inventari de mòduls

| Mòdul | Què comprova | Freqüència actual | Acció que emprèn | Notificació |
|---|---|---|---|---|
| `01-check-diem` | Saldo DIEM (`venice.py balance`) − 0,5 de marge ≥ `MIN_DIEM_RESERVE` (3) | Cada heartbeat (fase 0) | Si és baix: crea `sistema/state/diem_stop` si `worker.sh` és viu i **avorta tot el heartbeat** | Només log (`heartbeat.log`, `heartbeat.jsonl`) |
| `02-check-worker` | `pgrep worker.sh` | Cada heartbeat | Si no corre i no hi ha `diem_stop`: neteja `worker.lock` orfe, torna `running/`→`pending/`, reinicia `worker.sh` amb `nohup` | Només log |
| `03-check-failed` | Tasques a `tasks/failed/` amb >60 min (màx. 5) | Cada heartbeat | Reintenta (reset de `retries`, simplifica instruccions >200 caràcters) o mou a `failed_permanent/` (≥9 fallades o ≥3 regeneracions) | Només log |
| `04-check-needs-fix` | Obres amb `.needs_fix`; obres amb `.fixing` | Cada heartbeat | Puntuació 0 → tasca `translation` (pipeline V2); si no → tasca `fix`. Renombra `.needs_fix`→`.fixing`. Esborra `.fixing` quan hi ha una tasca `done` posterior | Només log |
| `05-check-supervision` | `sistema/scripts/check_supervision.py` → `MISSING_META` / `NEEDS_REVIEW` | Només si cua < 5 | Crea tasques `supervision` (crear `metadata.yml` o revisar qualitat i crear `.validated`/`.needs_fix`) | Només log |
| `06-check-translations` | Obres amb `original.md` no buit i sense `.validated` | Només si cua < 5 | Crea tasques `translate` amb model per gènere | Només log |
| `07-check-web-sync` | mtime de `obres/` vs `docs/*.html` | Cada heartbeat | Crea tasca `publish` (`build.py` + commit + push), fora del límit de cua | Només log |
| `08-check-maintenance` | Diumenge i cap manteniment fet en 7 dies; tasques `done/` > 7 dies | Cada heartbeat (efecte setmanal) | Crea tasca `maintenance`; **esborra** JSON de `done/` > 7 dies | Només log |
| `09-audit-catalog` | Marca de temps `state/.last_audit` > 12 h | Cada heartbeat (efecte cada 12 h) | `auditar-cataleg.sh --fix` | Només log |
| `10-generate-report` | Recompte de traduccions, `.validated`, `.needs_fix`, cua, worker | Cada heartbeat (fase 3) | `update_queue_status.py`; escriu `state/last_heartbeat_report.md` i `state/heartbeat_state.json`; crida `processar-propostes.sh` | Discord via `send-heartbeat-report.sh` — **ara desactivat** (`.disabled`) |
| `11-shutdown-report` | — (no el crida el heartbeat; el crida el worker en esgotar DIEM) | Per esdeveniment | Informe d'aturada a `state/shutdown_report_*.md` | `notificar.sh` |

### Observacions trobades en llegir els mòduls (no corregides — fora d'abast)

- `07-check-web-sync`: la condició `if [ "$obres_time" -gt "$docs_time" ] 2>/dev/null || true`
  sempre és certa → sempre crea tasca `publish` (si no n'hi ha cap).
- `06-check-translations`: assigna `claude-opus-4-7` / `claude-sonnet-4-6`, en contradicció
  amb `sistema/config/models.conf` i `CLAUDE.md` (kimi-k2-5 / llama-3.3-70b / qwen3-thinking).
  A més, en mode consolidació **no s'han de generar obres noves**.
- `04-check-needs-fix`: les instruccions de la tasca `fix` diuen «Commit+push».
- `10-generate-report`: referencia `scripts/informe_detallat.py`, que no existeix.

## 3. Proposta de jobs de Hermes

Principis:
- **Un job per comprovació** (PLA §T2.2), però agrupant els que comparteixen freqüència
  i no tenen sentit separats, per no multiplicar el cost del model orquestrador.
- Els jobs **no escriuen a `sistema/tasks/`** (cua obsoleta): o fan l'acció directament
  amb el skill `biblioteca-arion-worker`, o només informen.
- Comprovacions deterministes i barates → `script` (no_agent, silenciós si tot va bé),
  com els watchdogs existents (`gluetun-port-watchdog`, `Pi watchdog`).
- Res no fa `git push` sense vistiplau.
- Lliurament: `origin` (canal habitual de Pol) excepte on s'indica.

| # | Nom del job | Substitueix | Schedule | Tipus | Prompt / script (resum) | Skills | Deliver |
|---|---|---|---|---|---|---|---|
| J1 | `Arion — guarda DIEM` | `01` (+ `11`) | `0 */2 * * *` | script | `arion-diem-guard.sh`: llegeix saldo; si disponible (−0,5) < 3,0 crea `sistema/state/diem_stop` i avisa; si torna a ≥ 3,0 després del reset (00:01 UTC) l'esborra i avisa. Silenciós si no hi ha canvi d'estat | — | `origin` |
| J2 | `Arion — salut de la producció` | `02` + `03` | `*/30 * * * *` | script | `arion-health.sh`: detecta producció encallada (tasques a `running/` > 2 h, `worker.lock` orfe, fallides noves). **No reinicia `worker.sh`** (obsolet): només avisa. Quan T2.4 retiri el worker bash, s'adapta al skill | — | `origin` |
| J3 | `Arion — obres needs_fix` | `04` | `0 8,20 * * *` | agent | Llista obres amb `.needs_fix`; per a cadascuna llegeix el fitxer i, si DIEM ≥ 3,0, en corregeix **una** per execució amb `traduir_pipeline.py` (puntuació 0) o correccions dirigides; passa `pre_supervisio.py`; commit local per obra. Mai toca obres validades sense `.needs_fix` | `biblioteca-arion-worker`, `venice-model-routing` | `origin` |
| J4 | `Arion — supervisió de qualitat` | `05` | `0 14 * * *` | agent | Executa `check_supervision.py`; per a `MISSING_META` crea el `metadata.yml`; per a `NEEDS_REVIEW` revisa **una** obra (≥ 7/10 → `.validated`, < 7 → `.needs_fix` amb motius) | `biblioteca-arion-worker`, `venice-model-routing` | `origin` |
| J5 | `Arion — traduccions pendents` | `06` | *Desactivat* (`enabled: false`) | agent | En mode consolidació **no s'han de generar obres noves**. Es defineix desactivat; quan s'activi, model segons `models.conf` (mai `deepseek`/`glm`) i una obra per execució | `biblioteca-arion-worker`, `venice-model-routing` | `origin` |
| J6 | `Arion — sincronització web` | `07` | `30 6 * * *` | script | `arion-web-sync.sh`: compara mtime de `obres/` vs `docs/`; si cal, `python3 sistema/web/build.py` i commit local. **Sense push** fins que Pol ho autoritzi. Silenciós si està al dia | — | `origin` |
| J7 | `Arion — manteniment setmanal` | `08` | `0 4 * * 0` | script | Neteja `*Zone.Identifier`, `git gc --auto`, espai de disc, rotació de `sistema/tasks/done/` > 7 dies mentre la cua existeixi. Informa només si hi ha avisos | — | `origin` |
| J8 | `Arion — auditoria setmanal del catàleg` | `09` | `0 10 * * 0` | agent | **Ja existeix** (`929b6f1f1391`). Proposta: mantenir-lo; decidir si ha d'executar `auditar-cataleg.sh --fix` (com feia el mòdul cada 12 h) o seguir només informant | `biblioteca-arion-worker` | `origin` |
| J9 | `Arion — informe diari` | `10` | `0 9 * * *` | agent | **Ja existeix** (`07da592c79f7`). Proposta: afegir-hi el pas `update_queue_status.py` i l'escriptura de `state/heartbeat_state.json` si algun consumidor (web/dashboard) encara el llegeix. `processar-propostes.sh` es tracta a la tasca de notificacions (025) | `biblioteca-arion-worker` | `origin` |

## 4. Ordre de desplegament suggerit (quan Pol ho aprovi)

1. J1 i J2 (scripts silenciosos, sense cost de model) — mantenen la seguretat de pressupost.
2. Ajustar J8 i J9 (ja existeixen).
3. J6 i J7.
4. J3 i J4 (consumeixen DIEM: activar-los després de validar J1).
5. J5 es queda desactivat mentre duri el mode consolidació.
6. Quan tots estiguin actius i verificats una setmana, arxivar `heartbeat.sh` i
   `modules/` a `arxiu/orquestracio-obsoleta/` (tasca 120).

## 5. Decisions pendents per a Pol

- Freqüències proposades (especialment J2 a 30 min i J3 dues vegades al dia).
- Si J6 pot fer `git push` (publicar la web) o només commit local.
- Si J8 ha d'aplicar `--fix` automàticament.
- Si cal mantenir `heartbeat_state.json` / `last_heartbeat_report.md` (qui els llegeix?).
- Els scripts `arion-diem-guard.sh`, `arion-health.sh`, `arion-web-sync.sh` aniran a
  `~/.hermes/scripts/` (com `arion-dev-cron.sh`) i s'han d'escriure en una tasca posterior.
