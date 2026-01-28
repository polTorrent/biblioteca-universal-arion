# Instruccions Claude Code - Biblioteca Universal Arion

## ⚠️ AUTENTICACIÓ - PRIORITAT MÀXIMA

**SEMPRE usa subscripció Claude Pro/Max, MAI crèdits API.**

```bash
# Verificar ABANS de res:
claude auth status

# Ha de mostrar:
# "Authenticated via Claude subscription"

# Si demana API key → NO introduir-la!
# En lloc d'això:
claude auth login
```

**Per què?**
- Subscripció: Cost fix mensual ($20-200), ús il·limitat dins quota
- API: Pay-per-token, facturació variable i sorpreses
- Els crèdits API es reserven per futur mode on-demand d'usuaris
- Mateixos agents, mateixa qualitat, sense sorpreses de facturació

---

## Projecte

Biblioteca oberta i col·laborativa de traduccions al català d'obres clàssiques universals.

**Idioma de treball:** Català sempre per documentació, codi i comunicació.

---

## Arquitectura d'Agents

### Pipeline Complet de Traducció

```
FASE INICIAL
    │
    ▼
0. VERIFICAR AUTENTICACIÓ (subscripció, no API!)
    │
    ▼
Consell Editorial (Inicial) ──► Brief editorial, config
    │
    ▼
Pescador de Textos ──► Text original net
    │
    ▼
Calculador Costos ──► Pressupost, go/no-go
    │
    ▼
Checkpointer (INICIA SESSIÓ)
    │
    ▼
Investigador ──► Context històric, fonts
    │
    ▼
Glossarista ──► Glossari terminològic
    │
    ▼
════════════════════════════════════════
FASE TRADUCCIÓ (per cada chunk)
════════════════════════════════════════
    │
    ▼
Traductor ──► Traducció + notes N.T.
    │
    ▼
    ┌─────────────────────────────┐
    │                             │
    ▼                             │
Revisor Coherència                │ Iteració
    │                             │ (màx 3)
    ▼                             │
Perfeccionament ──────────────────┘
    │
    ▼
Anotador Crític ──► Notes erudites
    │
    ▼
Checkpointer (GUARDA ESTAT CHUNK)
    │
════════════════════════════════════════
FASE FINAL
════════════════════════════════════════
    │
    ▼
Fusió chunks
    │
    ▼
Introducció ──► Estudi introductori
    │
    ▼
Consell Editorial (Final) ──► Aprovació
    │
    ▼
════════════════════════════════════════
FASE PUBLICACIÓ (paral·lelitzable)
════════════════════════════════════════
    │
    ├──► Retratista ──► Retrat autor
    ├──► Portadista ──► Portada obra
    └──► Publisher ──► EPUB, PDF, HTML
    │
    ▼
Checkpointer (TANCA SESSIÓ) ──► Resum final
```

---

## Agents Principals

### Agents Nous (v2.0)

| Agent | Fitxer | Descripció |
|-------|--------|------------|
| **PerfeccionamentAgent** | `agents/perfeccionament_agent.py` | Fusió holística de naturalització + correcció IEC + estil. Reemplaça CorrectorAgent i EstilAgent. |
| **AnotadorCriticAgent** | `agents/anotador_critic.py` | Afegeix notes erudites (històriques, culturals, intertextuals, terminològiques). |

### Agent de Perfeccionament

Treballa en **tres dimensions simultànies**:

1. **Naturalització** (segons llengua origen)
   - Japonès: SOV→SVO, keigo, onomatopeies
   - Llatí: hipèrbatons, ablatius absoluts
   - Grec: partícules, compostos
   - + 17 llengües més

2. **Normativa Catalana (IEC)**
   - Ortografia, gramàtica, puntuació, lèxic

3. **Estil i Veu** (segons gènere)
   - Filosofia, narrativa, poesia, teatre, assaig...

**Prioritat en conflictes:**
```
VEU DE L'AUTOR > FLUÏDESA > NORMATIVA ESTRICTA
```

### Agent Anotador Crític

Tipus de notes:
- `[historic]` - Context històric
- `[cultural]` - Costums i pràctiques
- `[intertextual]` - Al·lusions a altres obres
- `[textual]` - Variants textuals
- `[terminologic]` - Conceptes tècnics
- `[geographic]` - Llocs mencionats
- `[prosopografic]` - Identificació de personatges

Densitats: `minima` | `normal` | `exhaustiva`

---

## Sistema de Checkpointing

El `Checkpointer` permet recuperar pipelines interromputs.

**Ubicació:** `utils/checkpointer.py`

```python
from utils import Checkpointer

# Iniciar sessió
checkpointer = Checkpointer()
checkpoint = checkpointer.iniciar(
    sessio_id="gilgamesh-2024",
    obra="Epopeia de Gilgamesh",
    autor="Anònim",
    llengua_origen="accadi",
)

# Guardar progrés
checkpointer.guardar_glossari(glossari)
checkpointer.iniciar_chunks(chunks_list)
checkpointer.chunk_completat("1", qualitat=8.5)

# Reprendre sessió interrompuda
if checkpointer.existeix("gilgamesh-2024"):
    checkpoint = checkpointer.carregar("gilgamesh-2024")
    pendents = checkpointer.obtenir_chunks_pendents()
```

---

## Configuració del Pipeline

```python
from pipeline import TranslationPipeline, PipelineConfig

config = PipelineConfig(
    # Revisió
    max_revision_rounds=2,
    min_quality_score=7.0,

    # Perfeccionament (NOU)
    enable_perfeccionament=True,
    perfeccionament_level="normal",  # lleuger, normal, intensiu
    max_perfeccionament_iterations=3,

    # Anotació crítica (NOU)
    enable_critical_notes=True,
    notes_density="normal",  # minima, normal, exhaustiva

    # Checkpointing (NOU)
    enable_checkpointing=True,

    # DEPRECATED - usar enable_perfeccionament
    enable_correction=False,
    enable_styling=False,
)

pipeline = TranslationPipeline(config)
```

---

## Agents Deprecats

Els següents agents estan **deprecats** i generaran warnings:

| Agent | Reemplaçat per |
|-------|---------------|
| `CorrectorAgent` | `PerfeccionamentAgent` |
| `EstilAgent` | `PerfeccionamentAgent` |

```python
# Això generarà un DeprecationWarning:
from agents import CorrectorAgent
agent = CorrectorAgent()  # ⚠️ DEPRECATED

# Usar en lloc seu:
from agents import PerfeccionamentAgent
agent = PerfeccionamentAgent()
```

---

## Estructura de Fitxers

```
biblioteca-universal-arion/
├── agents/
│   ├── base_agent.py              # Classe base ABC
│   ├── perfeccionament_agent.py   # NOU: Agent holístic
│   ├── anotador_critic.py         # NOU: Notes erudites
│   ├── translator_agent.py        # Traductor principal
│   ├── reviewer_agent.py          # Revisor de qualitat
│   ├── glossarista.py             # Glossaris terminològics
│   ├── corrector.py               # DEPRECATED
│   ├── agent_estil.py             # DEPRECATED
│   └── ...
├── pipeline/
│   └── translation_pipeline.py    # Pipeline principal
├── utils/
│   ├── logger.py                  # Sistema de logging
│   ├── checkpointer.py            # NOU: Persistència
│   └── dashboard.py               # Visualització
├── tests/
│   ├── test_perfeccionament.py    # NOU
│   ├── test_anotador_critic.py    # NOU
│   └── test_checkpointer.py       # NOU
└── obres/
    └── [categoria]/[autor]/[obra]/
```

---

## Ús Ràpid

### Traducció Simple

```python
from pipeline import TranslationPipeline, PipelineConfig

config = PipelineConfig(
    enable_perfeccionament=True,
    enable_critical_notes=False,
)
pipeline = TranslationPipeline(config)

result = pipeline.run(
    text=text_original,
    source_language="llatí",
    author="Sèneca",
    work_title="De Brevitate Vitae",
)

print(result.final_translation)
print(f"Qualitat: {result.quality_score}/10")
```

### Usar Agents Individualment

```python
from agents import PerfeccionamentAgent, PerfeccionamentRequest

agent = PerfeccionamentAgent()
result = agent.perfect(PerfeccionamentRequest(
    text="Text traduït a perfeccionar...",
    text_original="Original latin text...",
    llengua_origen="llatí",
    genere="filosofia",
    nivell="normal",
))
```

---

## Tests

```bash
# Executar tots els tests
python -m pytest tests/ -v

# Tests específics dels nous components
python -m pytest tests/test_perfeccionament.py -v
python -m pytest tests/test_anotador_critic.py -v
python -m pytest tests/test_checkpointer.py -v
```

---

## Notes

| Codi | Significat |
|------|------------|
| [T] | Traducció |
| [L] | Literària |
| [F] | Filosòfica |
| [H] | Històrica |
| [R] | Referència |
| [C] | Cultural |
| [B] | Biogràfica |
| [N.T.] | Nota del traductor |

---

## Criteris per Gènere

- **Filosofia:** precisió terminològica, claredat expositiva
- **Novel·la:** veu narrativa, ritme
- **Poesia:** sentit + ritme + so
- **Teatre:** oralitat natural
- **Assaig:** claredat argumentativa
- **Textos sagrats:** registre elevat però accessible
