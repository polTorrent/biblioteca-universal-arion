<p align="center">
  <strong>Biblioteca Universal Arion</strong><br>
  <em>Clàssics universals, en català, creats per tothom</em>
</p>

<p align="center">
  <a href="https://poltorrent.github.io/biblioteca-universal-arion/"><img alt="Web" src="https://img.shields.io/badge/web-GitHub_Pages-blue?style=flat-square"></a>
  <a href="LICENSE"><img alt="Codi: MIT" src="https://img.shields.io/badge/codi-MIT-green?style=flat-square"></a>
  <a href="https://creativecommons.org/licenses/by-sa/4.0/"><img alt="Traduccions: CC BY-SA 4.0" src="https://img.shields.io/badge/traduccions-CC_BY--SA_4.0-orange?style=flat-square"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white">
  <img alt="Obres" src="https://img.shields.io/badge/obres-107-purple?style=flat-square">
  <img alt="Autors" src="https://img.shields.io/badge/autors-86-purple?style=flat-square">
</p>

---

Biblioteca oberta de traduccions al **català** d'obres clàssiques universals — filosofia, narrativa, poesia, teatre, assaig i textos orientals. Edició crítica bilingüe amb glossari, notes i context acadèmic.

## Catàleg

**107 obres** de **86 autors**, des del sànscrit antic fins al segle XX, organitzades en 6 categories:

| Categoria | Obres | Autors destacats |
|-----------|:-----:|------------------|
| **Filosofia** | 23 | Plató, Aristòtil, Epictet, Sèneca, Marc Aureli, Heràclit, Spinoza, Nietzsche |
| **Narrativa** | 27 | Kafka, Txèkhov, Poe, Dostoievski, Boccaccio, Apuleu, Pu Songling |
| **Poesia** | 22 | Shakespeare, Safo, Baudelaire, Petrarca, Dante, Leopardi, Rilke, Li Bai |
| **Teatre** | 14 | Sòfocles, Eurípides, Aristòfanes, Èsquil, Ibsen, Strindberg, Zeami |
| **Oriental** | 12 | Laozi, Confuci, Zhuangzi, Matsuo Bashō, Kamo no Chōmei, Vyasa |
| **Assaig** | 9 | Ciceró, Montaigne, Plutarc, Sei Shōnagon, Pseudo-Longí |

**Llengües d'origen**: grec antic, llatí, anglès, alemany, francès, italià, rus, xinès clàssic, japonès clàssic, persa, sànscrit, hebreu antic i més.

### Obres destacades

| Obra | Autor | Llengua | Qualitat |
|------|-------|---------|:--------:|
| Meditacions | Marc Aureli | Llatí | 8.0 |
| Fragments | Heràclit | Grec | 8.6 |
| El retrat oval | E. A. Poe | Anglès | 8.5 |
| El llibre del coixí | Sei Shōnagon | Japonès | 8.0 |
| Capítols interiors | Zhuangzi | Xinès | 8.0 |
| Sonets (selecció) | Shakespeare | Anglès | 8.0 |
| Tao Te King | Laozi | Xinès | 8.0 |

> Qualitat avaluada en 3 dimensions: fidelitat al text, veu de l'autor i fluïdesa en català.

---

## Arquitectura

El projecte combina **traducció assistida per IA** amb **revisió humana col·laborativa**.

### Pipeline de traducció

```
Investigador → Glossarista → Chunker → [ Anàlisi → Traducció → Avaluació → Refinament ] → Fusió → Validació
```

Una cadena d'agents especialitzats processa cada obra:

- **Investigació**: context històric, cultural i filològic
- **Glossari**: terminologia clau amb transliteració i equivalències
- **Traducció enriquida**: amb context, few-shot i memòria entre fragments
- **Avaluació dimensional**: fidelitat (25%) + veu de l'autor (40%) + fluïdesa (35%)
- **Refinament iteratiu**: correcció automàtica segons feedback

### Worker autònom

Un **worker autònom** processa tasques contínuament amb:

- **Selector de models intel·ligent** — tria el model segons tipus de tasca i gènere
- **Rate-limit handling** — gestió automàtica de límits d'API
- **Validació post-execució** — comprova qualitat abans de commit

#### Models i costos

Configuració real a [`sistema/config/models.conf`](sistema/config/models.conf):

| Tasca | Model | Thinking | Cost DIEM |
|-------|-------|:--------:|-----------|
| Traducció filosofia/poesia/teatre | `kimi-k2-5` | on | n/d |
| Traducció narrativa/assaig | `llama-3.3-70b` | off | n/d |
| Traducció oriental | `qwen3-235b-a22b-thinking-2507` | on | n/d |
| Traducció (per defecte) | `llama-3.3-70b` | on | n/d |
| Fetch textos originals | `mistral-small-3-2-24b-instruct` | off | n/d |
| Revisió/supervisió/validació | `llama-3.3-70b` | off | n/d |
| Administració (metadata, glossaris, web, tests) | `llama-3.3-70b` | — | n/d |

> **Regla crítica**: MAI utilitzar models econòmics (`deepseek`, `glm`) per a traducció literària.

---

## Estructura del projecte

```
biblioteca-universal-arion/
├── obres/                    # Traduccions organitzades per categoria
│   ├── filosofia/
│   ├── narrativa/
│   ├── poesia/
│   ├── teatre/
│   ├── oriental/
│   └── assaig/
├── sistema/
│   ├── automatitzacio/       # Heartbeat, worker i notificacions
│   │   ├── heartbeat.sh      # Orquestrador (heartbeat modular)
│   │   ├── modules/          # Mòduls del heartbeat (01-check-diem … 11-shutdown-report)
│   │   ├── worker.sh         # Worker unificat (venice/hermes/hybrid)
│   │   └── notificar.sh      # Notificacions unificades
│   ├── config/
│   │   └── models.conf       # Configuració de models per tipus de tasca
│   ├── desenvolupament/      # Desenvolupament autònom (dev-worker, backlog)
│   ├── scripts/              # task_manager.py i scripts check_*.py
│   ├── tasks/                # Cua de tasques del worker
│   │   ├── pending/
│   │   ├── running/
│   │   ├── done/
│   │   └── failed/
│   ├── traduccio/            # Scripts i agents de traducció
│   │   ├── agents/           # Agents (narrador, client Venice…)
│   │   ├── traduir_venice.py # Executa traduccions
│   │   └── fetch_url.py      # Descarrega fonts externes
│   ├── tests/                # Tests (test_arion.sh, pytest)
│   ├── logs/                 # Logs del sistema
│   └── state/                # Estat del heartbeat
├── scripts/                  # Punts d'entrada (build.py, audiollibres…)
├── docs/                     # Web (GitHub Pages)
├── community/                # Guies de contribució
├── CLAUDE.md                 # Convencions per a agents
├── OPERACIONS.md             # Manual operatiu del sistema
└── PLA-REFACTOR.md           # Pla de refactorització
```

### Estructura d'una obra

```
obres/<categoria>/<autor>/<obra>/
├── metadata.yml          # Metadades: autor, llengua, estat, qualitat
├── original.md           # Text original (domini públic)
├── traduccio.md          # Traducció al català
├── glossari.yml          # Termes clau amb transliteració
├── notes.md              # Notes del traductor
├── introduccio.md        # Introducció crítica
├── portada.png           # Portada generada
└── fragments/            # Fragments editables per col·laboració
```

---

## Instal·lació

### Requisits

- **Python 3.11+**
- **Venice AI** — API key amb crèdits DIEM
- **Git**

### Clonar i configurar

```bash
# Clonar el repositori
git clone https://github.com/polTorrent/biblioteca-universal-arion.git
cd biblioteca-universal-arion

# Instal·lar dependències
pip install -e ".[dev]"

# Configurar Venice AI
export VENICE_API_KEY="la-teva-clau-api"
```

### Dependències principals

`anthropic` `pydantic` `rich` `tenacity` `httpx` `jinja2` `pyyaml` `markdown`

### Executar el worker

```bash
# Processar tasques pendents
bash sistema/automatitzacio/venice-worker.sh

# Veure estat de les tasques
ls sistema/tasks/pending/
ls sistema/tasks/done/

# Gestió de tasques
bash sistema/automatitzacio/task-manager.sh list
bash sistema/automatitzacio/task-manager.sh status
```

### Build de la web

```bash
python3 scripts/build.py          # Genera HTML a docs/
python3 scripts/build.py --clean # Rebuild complet
```

---

## Worker amb Hermes Agent

El worker pot executar-se automàticament via **Hermes Agent** (cronjobs gestionats):

```bash
# Configurar cronjobs
hermes cron create --name biblioteca-arion-worker \
  --schedule "every 60m" \
  --skill biblioteca-arion-worker \
  --skill venice-ai \
  --workdir ~/biblioteca-universal-arion
```

Vegeu el skill `biblioteca-arion-worker` per a la documentació completa.

---

## Com contribuir

Totes les traduccions es poden millorar. Pots:

- Corregir errors ortogràfics, gramaticals o de normativa
- Proposar millores de traducció o interpretació
- Afegir notes crítiques o context acadèmic
- Obrir discussions sobre passatges concrets
- Completar traduccions inacabades

Consulta [CONTRIBUTING.md](community/CONTRIBUTING.md) per més detalls.

---

## Llicències

| Component | Llicència |
|-----------|-----------|
| Traduccions | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| Codi | [MIT](LICENSE) |
| Textos originals | Domini públic |

---

## Enllaços

- [Web del projecte](https://poltorrent.github.io/biblioteca-universal-arion/)
- [Guia de contribució](community/CONTRIBUTING.md)
- [Projecte Hermes Agent](https://github.com/nousresearch/hermes-agent)

---

<p align="center"><strong>Biblioteca Universal Arion</strong> &copy; 2026</p>