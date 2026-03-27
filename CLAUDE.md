# CLAUDE.md — Biblioteca Universal Arion

## 🛑 MODE CONSOLIDACIÓ (actiu)

**NO CREAR TÍTOLS NOUS.** El catàleg té ~100 obres i moltes tenen problemes.
Dedica't EXCLUSIVAMENT a millorar les obres existents.

### Problemes a resoldre (per ordre de prioritat):
1. **CRÍTIC**: Obres sense original.md o amb contingut inventat/placeholder
2. **CRÍTIC**: Traduccions incompletes (<30% de l'original) o inventades
3. **ALT**: Fonts originals sense URL verificable al metadata.yml
4. **ALT**: Castellanismes i errors de normativa a les traduccions
5. **MITJÀ**: Glossaris inexistents o YAML invàlid
6. **MITJÀ**: Notes referenciades [^N] que no existeixen a notes.md
7. **BAIX**: Portades inexistents o placeholders
8. **BAIX**: Obres que no apareixen a la web (falta build)

### Workflow del worker en mode consolidació:
1. Executa `bash sistema/automatitzacio/auditar-cataleg.sh --fix` per generar tasques
2. Processa les tasques per ordre de prioritat (priority 1 primer)
3. Quan no hi ha tasques pendents, torna a executar l'auditoria
4. Si tot és ✅, avisa i espera noves instruccions

### Què NO fer:
- NO afegir obres noves a obra-queue.json
- NO executar consell-editorial.sh
- NO proposar títols nous al brain
- NO crear tasques de tipus "fetch" o "translate" per obres que no existeixin ja

### Com saber si una obra necessita atenció:
- Executa: bash sistema/automatitzacio/auditar-cataleg.sh
- Mira config/auditoria.json

## ⚠️ PROTOCOL ANTI-AL·LUCINACIÓ — OBLIGATORI EN TOTA TRADUCCIÓ

### REGLA ZERO: MAI INVENTAR CONTINGUT
No generis MAI text que no existeixi al document original. Si no tens
clar què diu l'original, PARA i demana aclariment. Una traducció amb
buits és infinitament millor que una traducció amb invencions.

### UNITATS DE VERIFICACIÓ SEGONS GÈNERE

Cada gènere té una "unitat" natural que serveix per comptar i verificar:

| Gènere | Unitat de verificació | Exemples d'identificador |
|--------|----------------------|--------------------------|
| Filosofia aforística | Aforisme | ### 195, **195.** |
| Filosofia tractadística | Secció/paràgraf | § 28, ### Cap. 5 |
| Novel·la | Paràgraf o capítol | Capítol XII, ¶ numerat |
| Poesia | Estrofa o poema | Sonet XIV, Estrofa 3 |
| Teatre | Escena o parlament | Acte II Escena 3, ANTÍGONA: |
| Assaig | Secció o paràgraf | I., II., ### Secció 5 |
| Textos orientals | Sutra/vers/capítol | Vers 42, Cap. XXIII |

Si el text no té numeració explícita, usa els PARÀGRAFS com a unitat
(separats per línia en blanc).

### PROCEDIMENT OBLIGATORI PER CADA CHUNK/BLOC

#### ABANS de traduir:
1. IDENTIFICA el gènere i la unitat de verificació adequada
2. COMPTA les unitats del bloc original
3. LLISTA els seus identificadors (números, títols, primers 5 mots)
4. REGISTRA: "Bloc: unitats [PRIMERA] a [ÚLTIMA], total: N"
5. LOCALITZA tots els elements de risc dins el bloc:
   - Cites entre cometes, guillemets «» "" ''
   - Diàlegs (PERSONATGE: text, o amb guió —)
   - Fragments en altres idiomes (llatí, grec, alemany...)
   - Versos incrustats dins prosa
   - Llistes o enumeracions

#### DURANT la traducció:
6. Tradueix unitat per unitat, mantenint un comptador intern
7. Després de CADA unitat que contingui un element de risc, VERIFICA:
   - He acabat la unitat sencera? (no només fins a la cita)
   - El text que escric a continuació existeix a l'original?
   - La pròxima unitat que tradueixo té correspondència a l'original?
8. REGLA FONAMENTAL SOBRE CITES I DIÀLEGS:
   Les cites, diàlegs, fragments en altres idiomes i qualsevol text
   entre cometes o guillemets que apareix DINS d'una unitat (aforisme,
   paràgraf, escena...) és CONTINGUT NORMAL A TRADUIR.
   NO és un senyal de final.
   NO indica que la unitat s'ha acabat.
   TRADUEIX la cita i CONTINUA amb el text que la segueix a l'original.

#### DESPRÉS de traduir:
9. RECOMPTE FINAL OBLIGATORI:
   - Unitats a l'original: ___
   - Unitats a la traducció: ___
   - Coincideixen? SÍ → continua. NO → PARA i corregeix.
10. VERIFICA que l'última unitat traduïda correspon a l'última unitat
    de l'original (compara primers mots).
11. VERIFICA que cap unitat de la traducció conté idees, arguments,
    descripcions o frases que no apareixen en absolut a l'original.

### SENYALS D'ALARMA — ESTÀS AL·LUCINANT SI:
- Escrius una unitat i no trobes el text original corresponent
- L'identificador de la unitat (número, títol) no existeix a l'original
- Acabes de traduir una cita/diàleg i el que escrius després no ho
  pots localitzar a l'original
- La traducció és molt més curta o llarga que l'original sense motiu
- Sents que estàs "completant" o "continuant" en lloc de traduir
- Estàs generant parlaments d'un personatge que no parla en aquell punt
- Inventes estrofes d'un poema que a l'original no existeixen
- Escrius paràgrafs narratius que no reconeixies fa un moment a l'original

### FORMAT DE VERIFICACIÓ (afegeix al final de cada chunk)

```
<!-- VERIFICACIÓ ANTI-AL·LUCINACIÓ
Gènere: [filosofia/novel·la/poesia/teatre/assaig/oriental]
Unitat de verificació: [aforisme/paràgraf/estrofa/escena/secció]
Original: unitats [PRIMERA] a [ÚLTIMA] (total: N)
Traducció: unitats [PRIMERA] a [ÚLTIMA] (total: N)
Coincideix: SÍ/NO
Elements de risc tractats: [cites/diàlegs/fragments llatí/etc.]
Primers mots última unitat original: "..."
Primers mots última unitat traducció: "..."
-->
```

### SI DETECTES QUE HAS AL·LUCINAT:
1. PARA immediatament
2. Indica quina és l'última unitat CORRECTAMENT traduïda
3. Torna a l'original i localitza on t'has perdut
4. Reprèn des de l'últim punt correcte
5. NO intentis "arreglar" el text inventat — esborra'l tot i re-tradueix

### VERIFICACIÓ AUTOMÀTICA
Executa el script de verificació després de cada traducció:
```bash
python3 scripts/verificar_traduccio.py <original.md> <traduccio.md> [gènere]
```

## 1. Visió del projecte

Biblioteca oberta de traduccions al **català** d'obres clàssiques universals (filosofia, narrativa, poesia, textos orientals). Edició crítica bilingüe amb glossari, notes i context acadèmic.

- **Traduccions**: CC BY-SA 4.0
- **Codi**: MIT
- **Originals**: domini públic
- **Web**: GitHub Pages via `docs/` (branch `gh-pages`) — build amb `python3 sistema/web/build.py`
- **URL web**: https://poltorrent.github.io/editorial-classica/
- **Python**: >= 3.11

## 2. Estructura del projecte

```
biblioteca-universal-arion/
├── agents/                  # Agents de traducció
│   ├── base_agent.py        # BaseAgent abstracte (CLI + API)
│   ├── traductor_classic.py, corrector_normatiu.py, glossarista.py...  # Agents V1
│   ├── venice_client.py     # Client Venice/GLM
│   ├── v2/                  # Pipeline V2
│   │   ├── pipeline_v2.py   # Orquestrador principal
│   │   ├── models.py        # Models Pydantic (AnalisiPreTraduccio, AvaluacioFidelitat...)
│   │   ├── analitzador_pre.py
│   │   ├── traductor_enriquit.py
│   │   ├── avaluador_dimensional.py
│   │   └── refinador_iteratiu.py
│   └── utils/               # Utilitats dels agents
├── core/                    # Nucli del sistema
│   ├── estat_pipeline.py    # Persistència d'estat (reprendre traduccions)
│   ├── memoria_contextual.py # Coherència entre chunks
│   └── validador_final.py   # Validació final de qualitat
├── utils/                   # Utilitats generals
│   ├── validators.py        # Validació de text d'entrada
│   ├── corrector_linguistic.py
│   ├── detector_calcs.py    # Detecció de calcs lingüístics
│   ├── checkpointer.py      # Checkpoint/resume de traduccions
│   ├── logger.py, metrics.py, dashboard.py
│   └── epub_generator.py
├── sistema/                 # Scripts operatius (reorganitzats)
│   ├── automatitzacio/      # heartbeat.sh, claude-worker-mini.sh, task-manager.sh, fix-structure.sh...
│   ├── traduccio/           # traduir_pipeline.py, traduir_*.py, cercador_fonts_v2.py, generar_portades.py...
│   └── web/                 # build.py, dashboard_server.py
├── obres/                   # Traduccions (per categoria/autor/obra)
│   ├── filosofia/           # Epictetus, Plató, Sèneca, Marc Aureli, Schopenhauer...
│   ├── narrativa/           # Kafka, Txèkhov, Poe, Melville, Akutagawa...
│   ├── oriental/            # Laozi (Tao Te King), Sutra del Cor
│   └── poesia/              # Shakespeare (Sonets)
├── config/
│   └── obra-queue.json      # Cua d'obres a traduir (heartbeat la llegeix)
├── web/                     # Templates i assets per la web
│   ├── templates/           # Jinja2: index.html, obra.html, base.html...
│   ├── css/                 # styles.css, obra.css...
│   └── js/                  # app.js, mecenatge.js...
├── docs/                    # Output HTML (GitHub Pages) — NO editar manualment
├── data/                    # JSON de catàleg i mecenatge
├── tests/                   # Tests pytest
├── dashboard/               # Dashboard web de monitorització
├── community/               # CONTRIBUTING.md
├── .github/workflows/build.yml  # CI: build + deploy a gh-pages
└── pyproject.toml           # Dependències i config (ruff, pytest)
```

## 3. Sistema autònom

### Heartbeat (`sistema/automatitzacio/heartbeat.sh`)
- **Cron**: cada 2 hores (`0 */2 * * *`)
- Analitza obres pendents a `config/obra-queue.json`
- Genera tasques JSON a `~/.openclaw/workspace/tasks/pending/`
- Supervisió: detecta traduccions sense validar, crea tasques de revisió
- Auto-fix: detecta `.needs_fix` i crea tasques correctores
- Comprova sincronització web, code reviews, tests
- Rotació de tasques completades (+7 dies)
- Genera report a `~/.openclaw/workspace/last_heartbeat_report.md`
- Comprova saldo DIEM abans de generar tasques

### Cua de tasques (`~/.openclaw/workspace/tasks/`)
```
tasks/
├── pending/    # Tasques esperant execució (JSON)
├── running/    # Tasca en execució
├── done/       # Completades (es roten cada 7 dies)
└── failed/     # Fallides (es reintenten fins a 2 cops)
```

Tipus de tasques: `translate`, `supervision`, `fix`, `code-review`, `test`, `publish`, `maintenance`

### Worker (`sistema/automatitzacio/claude-worker-mini.sh`)
- Processa tasques en loop infinit dins tmux (sessió `worker`)
- Crida `claude -p` amb `setsid -w` i `unset CLAUDECODE` (evita nested sessions)
- **Retry**: fins a 3 intents per tasca amb backoff exponencial
- **Rate limit**: pausa 30 min si detectat
- **Detecció de plans**: si Claude genera un pla sense executar, reintenta amb instruccions reforçades
- **Validació post-execució**: comprova que s'han creat/modificat fitxers realment
- **Safety**: màx 100 tasques/dia, pausa d'emergència si 5 errors consecutius
- **Timeout**: 30 min per tasca
- **Auto-commit + push** després de cada tasca exitosa
- Lockfile a `tasks/worker.lock`

### Task Manager (`sistema/automatitzacio/task-manager.sh`)
```bash
bash sistema/automatitzacio/task-manager.sh add <type> <instruction>
bash sistema/automatitzacio/task-manager.sh translate <autor> <títol> [llengua] [categoria]
bash sistema/automatitzacio/task-manager.sh list          # Llistar cua
bash sistema/automatitzacio/task-manager.sh status        # Estat worker
bash sistema/automatitzacio/task-manager.sh cancel <id>   # Cancel·lar tasca
bash sistema/automatitzacio/task-manager.sh clear [done|failed|pending|all]
bash sistema/automatitzacio/task-manager.sh review-all    # Code review de tot
```

## 4. Integració OpenClaw

- **Bot**: WhatsApp/Discord via GLM5 (Venice AI)
- **Skill**: `claude-code` — permet al bot executar tasques al repositori
- **Fitxers OpenClaw**: `~/.openclaw/workspace/`
  - `SOUL.md`: personalitat del bot
  - `HEARTBEAT.md`: estat del sistema
  - `skills/`: skills disponibles
- **DIEM**: moneda interna per pagar tasques — heartbeat comprova saldo mínim (2)
- **Venice client**: `agents/venice_client.py`

## 5. Convencions de codi

- **Python 3.11+**, type hints obligatoris
- **Pydantic v2** per models de dades (BaseModel, Field)
- **Agents**: hereten de `BaseAgent` (`agents/base_agent.py`)
  - Implementar `system_prompt` (property abstracta)
  - Opcionalment sobreescriure `process()`
  - Mode subscripció (CLI) vs API (SDK Anthropic)
- **Model per defecte**: `claude-sonnet-4-20250514`
- **Linter**: ruff (line-length=100, target py311)
- **Logging**: `utils/logger.py` — `AgentLogger`
- **Retry**: `tenacity` amb exponential backoff
- **Idioma**: codi en català (noms de classes, variables, comentaris, commits)
- **Dependències**: anthropic, pydantic, rich, python-dotenv, tenacity, httpx
- **Build web**: jinja2, pyyaml, markdown
- **IMPORTANT**: `unset CLAUDECODE` (o netejar de l'env) quan es crida `claude` des d'un subprocess per evitar error "nested sessions"

## 6. Pipeline de traducció V2

```
Investigador → Glossarista → Chunker → [per chunk: Anàlisi → Traducció → Avaluació → Refinament] → Fusió → Validació
```

### Agents V2 (`agents/v2/`)
1. **AnalitzadorPreTraduccio** — Analitza to, estil, paraules clau, recursos literaris, reptes
2. **TraductorEnriquit** — Tradueix amb context enriquit (anàlisi + glossari + few-shot)
3. **AvaluadorDimensional** — Avalua 3 dimensions:
   - Fidelitat (pes 25%): omissions, addicions, terminologia
   - Veu de l'autor (pes 40%): registre, to, ritme, idiosincràsies
   - Fluïdesa (pes 35%): sintaxi, lèxic, normativa IEC, llegibilitat
4. **RefinadorIteratiu** — Corregeix segons feedback (màx 1 iteració)

### Configuració pipeline (`ConfiguracioPipelineV2`)
- `llindar_qualitat`: 8.0/10 (global mínim per aprovar)
- `fer_investigacio`: recerca de context sobre l'autor
- `habilitar_persistencia`: reprendre traduccions interrompudes
- `habilitar_dashboard`: monitorització en temps real

### Llançar traducció
```bash
# Via script
python3 sistema/traduccio/traduir_pipeline.py obres/filosofia/plato/criton/

# Via codi
from agents.v2 import PipelineV2, ConfiguracioPipelineV2
pipeline = PipelineV2(config=ConfiguracioPipelineV2())
resultat = pipeline.traduir(text=text, llengua_origen="grec", autor="Plató", obra="Critó")
```

## 7. Estructura d'una obra

```
obres/<categoria>/<autor>/<obra>/
├── metadata.yml              # OBLIGATORI: títol, autor, llengua, revisió, estadístiques
├── original.md               # Text original (domini públic)
├── traduccio.md              # Traducció al català
├── glossari.yml              # Termes clau amb transliteració i traducció
├── notes.md                  # Notes del traductor (format: ## [n] Títol)
├── introduccio.md            # Introducció (opcional)
├── bibliografia.md           # Fonts (opcional)
├── portada.png               # Portada generada (opcional)
├── fragments/                # Fragments editables per col·laboració
├── discussions/              # Discussions crítiques
├── .validated                # Marca de qualitat aprovada (>= 7/10)
├── .needs_fix                # Marca de problemes (< 7/10, amb llista)
├── .fixing                   # En procés de correcció
├── .pipeline_state.json      # Estat de persistència del pipeline
└── .memoria_contextual.json  # Memòria entre chunks
```

### metadata.yml (exemple)
```yaml
obra:
  titol: "Enchiridion"
  titol_original: "Ἐγχειρίδιον"
  autor: "Epictetus"
  autor_original: "Ἐπίκτητος"
  traductor: "Editorial Clàssica"
  any_original: "c. 125 dC"
  any_traduccio: 2026
  llengua_original: "grec"
  descripcio: "Manual pràctic de filosofia estoica..."
seccions: 5
estadistiques:
  paraules_original: 487
  paraules_traduccio: 512
  notes: 8
  termes_glossari: 5
revisio:
  estat: "revisat"
  qualitat: 8.5
  data_revisio: "2026-01-25"
```

## 8. Tests

```bash
python3 -m pytest tests/ -v
```

Tests existents:
- `test_validators.py` — validació de text d'entrada
- `test_corrector_normatiu.py` — correcció lingüística
- `test_detector_calcs_angles.py` — detecció calcs anglesos
- `test_checkpointer_recovery.py` — checkpoint/resume
- `test_debug_agents.py` — debug dels agents
- `test_metrics.py` — mètriques
- `test_traductor.py` — traductor
- `test_plugins_nous.py` — plugins

Config: `pyproject.toml` → `[tool.pytest.ini_options]`, asyncio_mode = "auto"

## 9. Git i branching

- **Branch principal**: `main`
- **Deploy**: `gh-pages` (auto via GitHub Actions)
- **CI**: `.github/workflows/build.yml` — build + deploy a GitHub Pages en cada push a main
- **Commits**: en català, format descriptiu (`Afegir traduccio...`, `Corregir...`)
- **Commits automàtics del worker**: prefix `auto: <task_id>`
- **No hi ha branching strategy** — tot va directe a `main`
- **Auto-push**: el worker fa push automàtic després de cada tasca

## 10. Seguretat

**MAI accedir, llegir, modificar ni exposar:**
- `/mnt/c/` — filesystem Windows del host
- `~/.ssh/` — claus SSH
- `~/.config/` — configuració personal
- `.env`, `.env.local`, `secrets.yml`, `api_keys.txt` — secrets
- `~/.openclaw/workspace/` — no modificar directament (usar task-manager)

**Altres regles:**
- No cometre fitxers `.env` ni secrets al repo
- No fer `git push --force`
- No executar comandes destructives sense confirmació
- Respectar `.gitignore` (inclou `*.log`, `.env`, `Zone.Identifier`, etc.)

## 11. Comandes ràpides

```bash
# Build web
python3 sistema/web/build.py
python3 sistema/web/build.py --clean

# Gestió de tasques
bash sistema/automatitzacio/task-manager.sh list
bash sistema/automatitzacio/task-manager.sh status
bash sistema/automatitzacio/task-manager.sh add translate "Tradueix X de Y"

# Worker
bash sistema/automatitzacio/claude-worker-mini.sh          # Iniciar worker (foreground)
tmux new-session -d -s worker "cd ~/biblioteca-universal-arion && bash sistema/automatitzacio/claude-worker-mini.sh"

# Heartbeat manual
bash sistema/automatitzacio/heartbeat.sh

# Tests
python3 -m pytest tests/ -v

# Dashboard
bash dashboard.sh

# Linter
ruff check agents/ utils/ core/ sistema/
```

## 12. Problemes coneguts

- **Worker complet (`claude-worker.sh`)**: no funciona — usar `claude-worker-mini.sh`
- **Nested sessions**: si `CLAUDECODE=1` està definit i es crida `claude` des d'un subprocess, falla. Solució: `unset CLAUDECODE` o netejar env
- **Rate limits**: el worker pausa 30 min si es detecten. Les traduccions llargues poden trigar
- **Detecció de plans**: de vegades Claude genera plans en lloc d'executar. El worker v3 ho detecta i reintenta amb instruccions reforçades
- **Fitxers temporals a l'arrel**: hi ha molts fitxers `.html`, `.txt`, `.py` temporals d'extraccions a l'arrel que s'haurien de netejar (prefixats amb `_` o sense directori propi)
- **obra-queue.json desactualitzat**: els `status` no reflecteixen l'estat real de totes les obres. El heartbeat intenta actualitzar-lo
- **Zone.Identifier**: fitxers fantasma de Windows/WSL que s'han de netejar periòdicament
- **check_worker desactivat**: al heartbeat, `check_worker` està comentat perquè interfereix amb traduccions llargues
