# PLA DE REFACTOR INTEGRAL — Biblioteca Universal Arion

> **Estat:** proposta · **Data:** 2026-10-05 · **Autor:** Hermes (amb reconeixement del repo)
> **Objectiu:** passar d'un projecte viu però abandonat i acumulatiu a un projecte net,
> modular, testejat, autònom i sostingut que avanci sol aprofitant la quota lliure de
> la subscripció Claude.

---

## 1. Diagnòstic (estat real, 2026-10-05)

### 1.1 El projecte funciona, però està aturat i desordenat
- **Contingut:** 97 obres amb `metadata.yml`, 107 obres / 86 autors al catàleg, 6 categories.
- **Codi:** 226 fitxers `.py` + 72 fitxers `.sh`, 2.539 fitxers rastrejats per git.
- **Pes:** `sistema/` 204M · `docs/` 173M · `obres/` 149M · `web/` 96M · `.git/` **802M**.
- **Abandonament:** últim push reixit a `origin/main` el **2026-06-05**. Des del **2026-07-18**
  hi ha **16 commits locals** sense pujar. El worker està aturat, el heartbeat no corre,
  `sistema/state/diem_stop` existeix (DIEM aturat). Cua: 4 tasques a `pending/`, 1 a `done/`.

### 1.2 Problemes detectats (ordenats per impacte)

| # | Problema | Evidència | Impacte |
|---|----------|-----------|---------|
| P1 | **Push a GitHub trencat** | `remote: Permission ... denied to jordivinyalsferre-wq` | La web pública no s'actualitza des de juny; 16 commits orfes |
| P2 | **Historial git inflat** | `.git` = 802M; artefactes generats rastrejats (`docs/` 402 fitxers, `web/` 108) | Clons lents, difícil de mantenir |
| P3 | **Symlinks trencats** | `scripts/{deploy,serve,worker-watchdog,claude-worker-mini,improve-openclaw}.sh` i `informe_detallat.py` → destinacions inexistents | Errors silenciosos, confusió |
| P4 | **Serveis zombis** | `systemd` `claude-worker.service` apunta a un script inexistent; cron jobs Arion desactivats | Falsa sensació d'autonomia |
| P5 | **Automatització dispersa** | `heartbeat.sh` + `worker.sh` (venice/hermes/hybrid) + `task_manager.py` + `claude-worker.sh` (a `.openclaw/workspace`, còpia divergent) | Duplicació de lògica, difícil de raonar |
| P6 | **Cost descontrolat** | DIEM aturat; models `thinking=on`; sense pressupost explícit | Risc de despesa |
| P7 | **Qualitat sense xarxa de seguretat** | `test_arion.sh` (46/48), sense CI, sense pre-commit | Regressions invisibles |
| P8 | **Brutícia al repo** | `_tmp_hicks.txt` (3M), `*.bak.20260226` rastrejats, `Zone.Identifier`, còpia `.openclaw/workspace/` | Soroll |
| P9 | **Documentació desincronitzada** | `README.md` diu "models claude-opus-4-7 / deepseek-v3.2"; `models.conf` ja usa `kimi-k2-5`, `llama-3.3-70b`, `qwen3` | Agents confosos |
| P10 | **Sense autodesenvolupament** | Cap sistema aprofita la quota lliure de Claude Pro | El codi no millora sol |

### 1.3 El que JA està bé (conservar)
- Arquitectura v6 del heartbeat (orquestrador + 10 mòduls) i `worker.sh` unificat amb
  circuit breaker per model i *graceful shutdown*.
- `task_manager.py` amb dedup per hash i prioritats.
- `models.conf` **ja actualitzat** a models privats moderns (`kimi-k2-5`, `llama-3.3-70b`, `qwen3`).
- Autenticació Claude correcta: subscripció Pro (`poltorrentayala@gmail.com`), token a
  `~/.hermes/anthropic_pol.token`. Model dual subscripció/API ja documentat.
- Pipeline de traducció per agents (investigació → glossari → traducció → avaluació → refinament).

---

## 2. Objectiu i principis

**Objectiu:** un projecte on (a) el repositori sigui net i llegible, (b) el sistema
d'automatització sigui **un** i comprensible, (c) hi hagi tests + CI que protegeixin els
canvis, i (d) un worker aprofiti automàticament la quota lliure de Claude per fer avançar
el codi sense intervenció humana.

**Principis (segons preferències de Pol):**
1. **Fixes sistèmics, no pedaços.**
2. **No destructiu per defecte:** els canvis autònoms van a una branca (`auto/dev`), mai a `main`.
3. **Res de secrets ni credencials en text pla ni al repo.**
4. **Tot en català** (codi, logs, commits, docs).
5. **Canvis petits i freqüents**, cada un verificable.

---

## 3. Fases

### Fase 0 — Estabilització (immediata, poc risc)
- **T0.1** Arreglar el push: usar un PAT de `polTorrent` (a `~/.hermes/gh_pol.token`) via
  `credential.helper` **scopat al repo** o `insteadOf`. Verificar amb `git push --dry-run`.
- **T0.2** Eliminar els 6 symlinks trencats de `scripts/`.
- **T0.3** Desactivar/eliminar `~/.config/systemd/user/claude-worker.service` (apunta a un
  script inexistent) i arxivar els cron jobs Arion morts.
- **T0.4** Afegir al `.gitignore`: `_tmp_*`, `*.bak*`, `*:Zone.Identifier`, `sistema/state/*` runtime.
- **T0.5** Treure del control de versions `_tmp_hicks.txt` i els `*.bak.20260226`.

### Fase 1 — Higiene del repositori
- **T1.1** Decidir destí dels artefactes generats (`docs/`, `web/`): publicar via GitHub Pages
  des d'una branca `gh-pages` o un directori `dist/` **no rastrejat a `main`**.
- **T1.2** Reescrivir l'historial per treure artefactes pesats (opcions: `git filter-repo` o
  migrar a un repo nou net). **Requereix finestra de manteniment i vistiplau de Pol.**
- **T1.3** Unificar la còpia divergent de `.openclaw/workspace/biblioteca-universal-arion/`.

### Fase 2 — Refactor del sistema d'automatització
- **T2.1** Un sol orquestrador `arion` (o mantenir `heartbeat.sh`) que cobreixi:
  quota DIEM, worker, recuperació de fallides, supervisió, web sync, manteniment, auditoria.
- **T2.2** Extreure la lògica comuna a `sistema/lib/` (logging, notificació, git, models).
- **T2.3** Substituir els symlinks fràgils `scripts/ → sistema/` per un `Makefile` o
  un únic punt d'entrada `./arion <comanda>`.
- **T2.4** Definir **pressupost DIEM** explícit i tall automàtic (ja existeix `diem_stop`, formalitzar-lo).

### Fase 3 — Qualitat: tests + CI
- **T3.1** Ampliar `sistema/tests/` (unitat per a `task_manager.py`, parser de metadata,
  `build.py`) fins a cobrir els camins crítics.
- **T3.2** GitHub Actions: `lint` (ruff/shellcheck) + `test` (pytest) + `build` (web) a cada push/PR.
- **T3.3** Pre-commit local (ruff, shellcheck, detecció de secrets).

### Fase 4 — Autodesenvolupament (quota Claude)  ← **ja implementat, vegeu §4**
- **T4.1** `quota-probe.py` — detector de quota lliure.
- **T4.2** `dev-worker.sh` — bucle autònom que resol tasques del backlog quan hi ha quota.
- **T4.3** Backlog viu + encuament de tasques.
- **T4.4** Programació via Hermes cron (cada 20–30 min).
- **T4.5** (Opcional) Fallback a `claude --cloud` quan la quota Pro s'esgota.

### Fase 5 — Observabilitat i documentació
- **T5.1** Actualitzar `README.md` i `OPERACIONS.md` a l'estat real (models, arquitectura).
- **T5.2** Dashboard d'estat: quota, backlog, últimes tasques, cost DIEM.
- **T5.3** Report diari a Discord amb els canvis del dia.

### Fase 6 — Represa de la producció
- **T6.1** Reprendre traduccions amb `models.conf` actual (kimi-k2-5 per a literatura).
- **T6.2** Revisar les 4 tasques pendents i les 16 commits orfes.
- **T6.3** Reactivar la publicació web un cop el push funcioni.

---

## 4. Sistema d'autodesenvolupament (implementat)

Ubicació: `sistema/desenvolupament/`

```
sistema/desenvolupament/
├── quota-probe.py            # detecta FREE / LIMIT / ERROR de la subscripció
├── dev-worker.sh             # bucle autònom (branca auto/dev, sense push)
├── status.sh                 # estat: quota + backlog + commits
├── enqueue.sh                # afegir tasques al backlog
├── claude-dev-guard.sh       # hook PreToolUse: bloqueja ordres destructives
├── claude-dev-settings.json  # settings del Claude Code autònom
├── PROMPT.md                 # instruccions permanents de cada tasca
├── state/quota.json          # últim resultat de la sonda
└── backlog/{pending,running,done,failed}/
```

**Com funciona:**
1. `quota-probe.py` fa una prova mínima amb `claude` (Haiku, 1 torn, sense eines) i
   classifica: `FREE` / `LIMIT` / `ERROR`. És el **detector d'ús lliure de la subscripció**.
2. `dev-worker.sh` fa una passada: per cada tasca pendent, comprova la quota; si és `FREE`,
   executa Claude Code amb la tasca; commit a la branca `auto/dev`; passa a la següent.
3. S'atura sol quan: s'esgota la quota, s'acaba el backlog, o hi ha 3 errors seguits.
4. **Mai fa push i mai toca `main`.** La fusió la decideix una persona (`git merge auto/dev`).
5. Un guard PreToolUse bloqueja `git push`, `--force`, `reset --hard`, `rm -rf /`, `sudo`,
   escriptura a `.env` i claus.

**Posada en marxa:**
```bash
cd ~/biblioteca-universal-arion/sistema/desenvolupament
python3 quota-probe.py          # comprova quota ara
bash status.sh                  # estat del sistema
bash dev-worker.sh --dry-run    # veure què faria
bash dev-worker.sh              # una passada real (fins a 6 tasques)
```

**Programació (Hermes cron, cada 20 min):** un job que executa `dev-worker.sh` (que ja
s'autolimita). Vegeu `sistema/desenvolupament/README.md`.

---

## 5. Riscos i obertures

| Risc | Mitigació |
|------|-----------|
| Canvis autònoms trenquen `main` | Branca `auto/dev` + revisió humana abans de fusionar |
| Claude executa ordres destructives | Guard PreToolUse + `--dangerously-skip-permissions` acotat per settings |
| Reescriure l'historial espatlla el remuntador | Fase 1.2 requereix **vistiplau explícit** i còpia de seguretat prèvia |
| Cost DIEM fora de control | Pressupost explícit + `diem_stop` formalitzat (Fase 2.4) |
| Quota Pro compartida amb altres projectes | La sonda detecta `LIMIT` i el worker s'atura net |

**Obertures per a Pol:**
- ¿Publicar la web des de `gh-pages` o des d'un `dist/` no rastrejat?
- ¿Reescriure l'historial (Fase 1.2) o acceptar el `.git` de 802M?
- ¿Pressupost DIEM mensual objectiu?
- ¿Model per defecte del dev-worker: `opus` (millor) o `sonnet` (més quota disponible)?

---

## 6. Primeres tasques encuades al backlog

Vegeu `sistema/desenvolupament/backlog/pending/`. Les 10 primeres cobreixen les
Fases 0–1 i són de baix risc. Les que requereixen decisió humana estan marcades
`REQUEREIX VISTIPLAU` a la capçalera i el worker les salta.
