# Biblioteca Universal Arion — Context per a agents

## Què és
Biblioteca oberta de traduccions al **català** d'obres clàssiques universals (domini
públic), amb edició crítica bilingüe: original, traducció, glossari i notes erudites.
Web pública a GitHub Pages.

## Arquitectura (v3 — Hermes com a orquestrador)

> **Principi:** Hermes fa tota l'**orquestració** (planificació, cua, execució,
> notificacions, cost). El projecte aporta només el **domini**.

```
Hermes cron ──► agent orquestrador (model econòmic)
                  ├── skill biblioteca-arion-worker   (què fer i com)
                  ├── skill venice-ai / venice-model-routing (models i cost)
                  ├── tools: terminal, file, web
                  ├── invoca el DOMINI:
                  │     sistema/traduccio/traduir_pipeline.py
                  │     sistema/traduccio/pre_supervisio.py
                  │     sistema/web/build.py
                  └── lliura resultats a Discord/Telegram (natiu)
```

### Domini (això SÍ que es manté)
- `sistema/traduccio/` — pipeline i agents (investigador, glossarista, traductor,
  chunker, anotador, avaluador, corrector, portadista, narrador, `venice_client`…)
- `sistema/web/build.py` + `templates/` — construcció de la web
- `core/` — `validador_final`, `memoria_contextual`, `estat_pipeline`
- `utils/calcs_plugins/` — càlculs per llengua (grec, llatí, xinès…)
- `obres/`, `corpus_estil/`, `fonts/` — contingut i corpus
- `sistema/config/` — `models.conf`, `authors.yaml`, `diem_costs.conf`

### Orquestració pròpia (OBSOLETA — no ampliar)
`heartbeat.sh`, `worker.sh`, `venice-worker.sh`, `task-manager.sh`, `notificar*.sh`,
`system-brain.sh`, `millora-continua.sh`… Hermes els substitueix. Vegeu
`PLA-REFACTOR.md` §1.1 i `arxiu/orquestracio-obsoleta/INVENTARI.md`.

## Autenticació (IMPORTANT)
- **Claude Code (desenvolupament intern):** subscripció Pro/Max, **mai crèdits API**.
  Verifica amb `claude auth status`.
- **Usuaris web (on-demand):** crèdits API només quan paguen per traducció.
- Els agents detecten el context: `CLAUDECODE=1` → subscripció; context web → API.

## Convenis
- Idioma: **català** (codi, comentaris, commits, docs, logs).
- Mode **CONSOLIDACIÓ**: qualitat > quantitat; mai < 7/10.
- Mínim DIEM: 3.0 (aturar si menys).
- Commit per tasca (no batch).
- No generar obres noves en mode consolidació.

## Models (`sistema/config/models.conf`)
- Traducció literatura: `kimi-k2-5` (filosofia/poesia/teatre), `llama-3.3-70b`
  (narrativa/assaig), `qwen3-235b-a22b-thinking-2507` (oriental).
- **MAI** models econòmics (`deepseek`, `glm`) per a traducció literària.

## Desenvolupament autònom (quota Claude)
Sistema a `sistema/desenvolupament/`: `quota-probe.py` detecta quota lliure de la
subscripció; `dev-worker.sh` resol tasques del backlog amb Claude Code en una branca
`auto/dev` (**mai push, mai `main`**); cron de Hermes cada 30 min.
Pla mestre: `PLA-REFACTOR.md`.

## Estructura d'una obra
```
obres/<categoria>/<autor>/<obra>/
├── metadata.yml      # autor, llengua, estat, qualitat
├── original.md       # text original (domini públic)
├── traduccio.md      # traducció ([^N] notes, terme[T] glossari)
├── glossari.yml      # id, grec/llatí, transliteració, traducció, definició
├── notes.md          # notes erudites (## [N] Títol)
├── introduccio.md
└── portada.png
```

## Criteris per gènere
- Filosofia: precisió terminològica · Novel·la: veu narrativa
- Poesia: sentit + ritme · Teatre: oralitat · Oriental: fidelitat a la tradició

## Prohibicions
- No generar obres noves en mode consolidació.
- No modificar obres validades sense `.needs_fix`.
- No aturar el worker sense aturada neta.
- No `git push` des del worker de desenvolupament autònom.
