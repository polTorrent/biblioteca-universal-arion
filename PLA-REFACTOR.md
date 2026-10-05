# PLA DE REFACTOR INTEGRAL — Biblioteca Universal Arion

> **Estat:** proposta v2 (revisada amb l'òptica "Hermes com a orquestrador") · **Data:** 2026-10-05
> **Objectiu:** eliminar l'orquestració pròpia que ha quedat obsoleta, quedar-nos
> només amb el **domini** (traducció, qualitat, web, contingut) i deixar que Hermes
> + el model orquestrador facin la resta.

---

## 1. Canvi de paradigma: Hermes substitueix la infraestructura pròpia

El projecte va construir la seva pròpia maquinària d'orquestració (heartbeat, workers,
cua de tasques, notificacions, supervisor, "brain") **perquè no hi havia un agent
general que ho fes**. Ara hi és: **Hermes + un model orquestrador econòmic** (DeepSeek
V4.1 Flash) cobreixen de sèrie tot això. Per tant, bona part de `sistema/automatitzacio/`
ja no cal — **no s'ha d'unificar, s'ha d'esborrar i delegar**.

### 1.1 Mapa d'obsolescència

| Peça pròpia | Línies | Què fa | Substitut Hermes |
|-------------|-------:|--------|------------------|
| `heartbeat.sh` + `modules/00–11` | ~840 | Planificar, comprovar salut, omplir cua, informes | **Cron de Hermes** (un job per comprovació) |
| `worker.sh` / `venice-worker.sh` / `hermes-worker.sh` | ~1.830 | Executar tasques de traducció/revisió | **Skill `biblioteca-arion-worker`** + agent Hermes |
| `task-manager.sh` + `task_manager.py` | ~520 | Cua amb dedup, prioritats, retry | **Cua nativa de Hermes** (cron jobs) o cua mínima de domini |
| `notificar.sh` + `notificar-usuari.sh` + `enviar-informe-discord.sh` | ~335 | Notificacions, rate limiting, fallbacks | **Lliurament natiu** Discord/Telegram |
| `system-brain.sh` + `millora-continua.sh` | ~1.450 | Bucles d'auto-millora i decisió | **Raonament de l'agent** + skills |
| `monitor-arion.sh` + `worker-status.sh` + `arion-start/stop.sh` | ~370 | Monitoratge i arrencada/aturada | Cron + `status.sh` |
| `model_selector.py` + `diem-optimizer` | — | Triar model i optimitzar cost | **Routing de Hermes** (skill `venice-model-routing`) |
| `hermes_task_executor.py` | — | Pont cap a Hermes | **Natiu** (ja no cal pont) |
| `supervisor-retire-tasks.py` + `consell-editorial.sh` | ~200 | Supervisió / consell | Agent Hermes |
| `reset-diem.sh`, `boto_propostes_watchdog.sh` | ~85 | Tasques periòdiques | Cron de Hermes |

**Total aproximat: ~5.300 línies** d'orquestració pròpia candidata a desaparèixer.

### 1.2 Què SÍ que es conserva (és el valor del projecte)

| Peça | Per què es conserva |
|------|---------------------|
| `sistema/traduccio/**` (agents: investigador, glossarista, traductor, chunker, anotador, avaluador, corrector, portadista, narrador, venice_client…) | És el **pipeline de domini**; Hermes l'invoca com a eina |
| `sistema/web/build.py` + `templates/` | Construcció de la web |
| `utils/calcs_plugins/**` | Càlculs per llengua (grec, llatí, xinès…) |
| `core/**` (`validador_final`, `memoria_contextual`, `estat_pipeline`) | Lògica de qualitat i estat |
| `sistema/config/**` (`models.conf`, `authors.yaml`, `diem_costs.conf`) | Configuració de domini |
| `obres/**`, `corpus_estil/**`, `fonts/**` | Contingut i corpus |
| Bot de propostes (`propostes_*.py`, `formulari_handler.py`) | Funcionalitat pública |

### 1.3 A revisar (ni blanc ni negre)
- `task_manager.py` — pot quedar com a **cua de domini** mínima, o desaparèixer si el
  volum de tasques no ho justifica.
- `pre_supervisio.py` (592) + `check_supervision.py` / `check_translations.py` — lògica
  de domini útil; cal decidir si passa a skill o es manté com a script.
- `sistema/dashboard/` — ¿es conserva com a UI o es substitueix per un informe de Hermes?

### 1.4 Patró objectiu

```
Hermes cron  ──►  agent (orquestrador DeepSeek V4.1 Flash)
                    ├── skill biblioteca-arion-worker   (què fer i com)
                    ├── skill venice-ai / venice-model-routing  (models i cost)
                    ├── tools: terminal, file, web
                    ├── invoca DOMINI: traduir_pipeline.py, build.py, …
                    └── lliura resultats a Discord/Telegram (natiu)
```

Hermes és el **sistema operatiu**; el projecte només aporta el **domini**.

---

## 2. Diagnòstic de l'estat real (2026-10-05)

- **Contingut:** 97 obres amb `metadata.yml`; catàleg de 107 obres / 86 autors.
- **Codi:** 226 `.py` + 72 `.sh`; 2.539 fitxers rastrejats; `.git` = **802 MB**.
- **Abandonament:** últim push a `origin/main` el **2026-06-05**; **16 commits orfes**;
  worker aturat; DIEM aturat (`sistema/state/diem_stop`).
- **Problemes:** push trencat (403, credencial d'un altre compte) · historial inflat
  (artefactes generats rastrejats) · 6 symlinks trencats · serveis zombis
  (`claude-worker.service`, cron jobs morts) · automatització duplicada
  (`sistema/` vs `.openclaw/workspace/`) · README desincronitzat.

---

## 3. Objectiu i principis

**Objectiu:** un projecte **petit i net** on (a) el repo sigui llegible, (b) l'agent
Hermes faci tota l'orquestració, (c) el domini quedi testejat i aïllat, i (d) un worker
aprofiti la quota lliure de Claude per fer avançar el codi.

**Principis:**
1. **Esborrar abans que construir.** Cada línia d'orquestració pròpia que Hermes ja fa, fora.
2. **Fixes sistèmics, no pedaços.**
3. **No destructiu per defecte:** els canvis autònoms van a `auto/dev`, mai a `main`.
4. **Res de secrets ni credencials en text pla.**
5. **Tot en català.**

---

## 4. Fases (revisades)

### Fase 0 — Estabilització (immediata, poc risc)
- **T0.1** Arreglar el push (PAT de `polTorrent`) — **vistiplau humà**.
- **T0.2** Eliminar els 6 symlinks trencats de `scripts/`. ✔ *(fet)*
- **T0.3** Desactivar/eliminar `claude-worker.service` i arxivar els cron jobs Arion morts.
- **T0.4/T0.5** `.gitignore` (runtime, temporals, `Zone.Identifier`) i treure brutícia rastrejada.

### Fase 1 — Higiene del repositori
- **T1.1** Treure els artefactes generats (`docs/`, `web/`) de `main` → publicar des de
  `gh-pages` o un `dist/` no rastrejat.
- **T1.2** Reescriure l'historial per aprimar `.git` (o migrar a repo net) — **vistiplau**.
- **T1.3** Unificar/eliminar la còpia divergent `.openclaw/workspace/biblioteca-universal-arion/`.

### Fase 2 — **Eliminar l'orquestració pròpia i delegar-la a Hermes**  ← reescrita
- **T2.1** **Inventari i arxiu**: moure a `arxiu/orquestracio-obsoleta/` tot el de §1.1
  (no esborrar encara; primer arxivar i verificar que res no ho crida).
- **T2.2** **Migrar el heartbeat a cron de Hermes**: un job per comprovació
  (DIEM, salut del worker, fallides, `needs_fix`, supervisió, traduccions, web-sync,
  manteniment, auditoria, informe).
- **T2.3** **Substituir les notificacions** (`notificar*.sh`) pel lliurament natiu de Hermes.
- **T2.4** **Retirar els workers bash** un cop el skill `biblioteca-arion-worker` cobreixi
  les mateixes tasques via agent.
- **T2.5** **Routing de models i cost** via Hermes (`venice-model-routing`) + guardrails
  de pressupost DIEM en config, no en bash.
- **T2.6** Esborrar `system-brain.sh` i `millora-continua.sh` (substituïts pel raonament
  de l'agent).

### Fase 3 — Qualitat: tests + CI
- **T3.1** Tests per al **domini** (`traduir_pipeline.py`, parser de metadata, `build.py`).
- **T3.2** GitHub Actions: lint + tests + build a cada push/PR.
- **T3.3** Pre-commit local (ruff, shellcheck, detecció de secrets).

### Fase 4 — Autodesenvolupament (quota Claude)  ← **ja implementat** (vegeu §6)
- `quota-probe.py` + `dev-worker.sh` + backlog + cron Hermes cada 30 min.

### Fase 5 — Observabilitat i documentació
- **T5.1** Actualitzar `README.md` / `OPERACIONS.md` / `CLAUDE.md` a l'estat real
  (Hermes com a orquestrador, domini aïllat).
- **T5.2** Informe d'estat via Hermes (quota, backlog, últimes tasques, cost DIEM).

### Fase 6 — Represa de la producció
- Reprendre traduccions amb `models.conf` actual; revisar les 16 commits orfes; reactivar la web.

---

## 5. Impacte esperat

| Mètrica | Abans | Objectiu |
|---------|------:|---------:|
| Línies d'orquestració pròpia | ~5.300 | ~0 |
| Fitxers `.sh` | 72 | < 15 |
| `.git` | 802 MB | < 50 MB |
| Punt d'entrada | 20+ scripts | cron Hermes + skill |
| Superfície de fallada | alta | baixa |

---

## 6. Sistema d'autodesenvolupament (implementat)

Vegeu `sistema/desenvolupament/README.md`. Resum: `quota-probe.py` detecta quota lliure
de la subscripció; `dev-worker.sh` resol tasques del backlog amb Claude Code en una branca
`auto/dev` (mai push, mai `main`); cron Hermes cada 30 min; guard PreToolUse contra ordres
destructives.

---

## 7. Riscos i obertures

| Risc | Mitigació |
|------|-----------|
| Esborrar orquestració encara en ús | Fase 2.1 **arxiva** primer; esborrar només després de verificar |
| Reescriure l'historial espatlla el remot | Vistiplau explícit + còpia de seguretat |
| Cost DIEM descontrolat | Guardrails a la config de Hermes, no a bash |
| Dependència total de Hermes | El domini (`sistema/traduccio/`) és autònom i invocable a mà |

**Decisions que calen de Pol:**
1. Web pública: `gh-pages` o `dist/` no rastrejat?
2. Reescriure l'historial (802 MB) o acceptar-lo?
3. Pressupost DIEM mensual objectiu?
4. Model per defecte del dev-worker: `opus` o `sonnet`?
5. Dashboard: conservar la UI o substituir-la per un informe de Hermes?
