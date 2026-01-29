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

---

## Estructura de Fitxers

```
biblioteca-universal-arion/
├── agents/
│   ├── base_agent.py              # Classe base ABC
│   ├── perfeccionament_agent.py   # Agent holístic (correcció + estil)
│   ├── anotador_critic.py         # Notes erudites
│   ├── translator_agent.py        # Traductor principal
│   ├── reviewer_agent.py          # Revisor de qualitat
│   ├── glossarista.py             # Glossaris terminològics
│   ├── portadista.py              # Generació portades
│   └── v2/                        # Pipeline V2
│       ├── pipeline_v2.py         # Orquestrador principal
│       ├── analitzador_pre.py     # Anàlisi pre-traducció
│       ├── traductor_enriquit.py  # Traductor amb context ric
│       ├── avaluador_dimensional.py # Avaluació 3D
│       ├── refinador_iteratiu.py  # Millora iterativa
│       └── models.py              # Models de dades
├── pipeline/
│   └── translation_pipeline.py    # Pipeline V1 (compatible)
├── utils/
│   ├── logger.py                  # Sistema de logging
│   ├── checkpointer.py            # Persistència sessions
│   └── dashboard.py               # Visualització
├── scripts/
│   └── build.py                   # Generador HTML
├── web/
│   ├── templates/                 # Templates Jinja2
│   ├── css/                       # Estils
│   └── js/                        # JavaScript
├── docs/                          # Web generada
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

---

## Sistema d'Avaluació Dimensional (v2)

### Concepte

El sistema v2 separa l'avaluació de traduccions en **tres dimensions ortogonals**, cada una amb el seu avaluador especialitzat:

| Dimensió | Pes | Pregunta clau |
|----------|-----|---------------|
| **Fidelitat** | 25% | El significat es preserva? |
| **Veu de l'Autor** | 40% | El to i estil es mantenen? |
| **Fluïdesa** | 35% | Sona natural en català? |

### Per què és millor?

1. **Feedback específic**: Cada dimensió dona instruccions accionables
2. **Prioritats clares**: VEU > FIDELITAT > FLUÏDESA
3. **Refinament iteratiu**: Bucle fins a puntuació ≥ 8/10

### Ús bàsic

```python
from agents.v2 import AvaluadorDimensional, ContextAvaluacio

avaluador = AvaluadorDimensional()
context = ContextAvaluacio(
    text_original="Cogito, ergo sum.",
    text_traduit="Penso, per tant existeixo.",
    llengua_origen="llatí",
    autor="Descartes",
    genere="filosofia",
)

resultat = avaluador.avaluar(context)

print(f"Puntuació global: {resultat.puntuacio_global}/10")
print(f"Aprovat: {resultat.aprovat}")
print(resultat.instruccions_refinament)
```

### Mètode ràpid

```python
resultat = avaluador.avaluar_rapid(
    text_original="...",
    text_traduit="...",
    llengua_origen="japonès",
    autor="Akutagawa",
    genere="narrativa",
)
```

### Llindars d'aprovació

```python
from agents.v2.models import LlindarsAvaluacio

llindars = LlindarsAvaluacio(
    global_minim=8.0,        # Puntuació global mínima
    veu_autor_minim=7.5,     # Veu de l'autor mínima
    fidelitat_minim=7.0,     # Fidelitat mínima
    fluidesa_minim=7.0,      # Fluïdesa mínima
    max_iteracions=3,        # Màx refinaments
)
```

## Analitzador Pre-Traducció (v2)

### Concepte

Segons la recerca (MAPS - Multi-Aspect Prompting), analitzar el text ABANS de traduir millora significativament la qualitat, reduint la literalitat i preservant la veu de l'autor.

### Què identifica

1. **Paraules clau**: Termes crítics amb recomanacions de traducció
2. **To de l'autor**: Ironia, solemnitat, humor, registre...
3. **Recursos literaris**: Metàfores, anàfores, ritme...
4. **Reptes anticipats**: Estructures difícils, culturemes, jocs de paraules...
5. **Recomanacions**: Què prioritzar i què evitar

### Ús bàsic

```python
from agents.v2 import AnalitzadorPreTraduccio

analitzador = AnalitzadorPreTraduccio()
analisi = analitzador.analitzar(
    text="Quaeris quid sit libertas?...",
    llengua_origen="llatí",
    autor="Sèneca",
    genere="filosofia",
)

print(analisi.resum())  # Resum llegible
print(analisi.to_context_traduccio())  # Per passar al traductor
```

### Context enriquit complet

```python
from agents.v2 import AnalitzadorPreTraduccio, SelectorExemplesFewShot

analitzador = AnalitzadorPreTraduccio()
selector = SelectorExemplesFewShot()

# Preparar tot el context d'un cop
context = analitzador.preparar_context(
    text="Text original...",
    llengua_origen="japonès",
    autor="Akutagawa",
    glossari={"愚か": "estúpid"},
    exemples_fewshot=selector.seleccionar("japonès", "narrativa"),
)

# Generar prompt per al traductor
prompt_context = context.to_prompt_context()
```

---

## Traductor Enriquit (v2)

### Concepte

El TraductorEnriquit utilitza el context de l'AnalitzadorPreTraduccio per produir traduccions menys literals i més literàries. Prioritza VEU > FLUÏDESA > LITERALITAT.

### Diferències amb v1

| Aspecte | Traductor v1 | Traductor v2 |
|---------|--------------|--------------|
| Context | Mínim (autor, obra) | Ric (anàlisi, exemples, glossari) |
| Instruccions | Genèriques | Específiques per text |
| Sortida | Només text | Text + decisions + avisos |
| Literalitat | Tendència literal | Anti-literalitat explícita |

### Ús bàsic

```python
from agents.v2 import TraductorEnriquit, ContextTraduccioEnriquit

traductor = TraductorEnriquit()
resultat = traductor.traduir_simple(
    text="Cogito ergo sum",
    llengua_origen="llatí",
    autor="Descartes",
    genere="filosofia",
)

print(resultat.traduccio)
print(resultat.decisions_clau)
print(resultat.confianca)
```

### Flux complet amb anàlisi

```python
from agents.v2 import TraductorAmbAnalisi

traductor = TraductorAmbAnalisi()

resultat, analisi = traductor.traduir(
    text="Text original...",
    llengua_origen="japonès",
    autor="Akutagawa",
    genere="narrativa",
)

# analisi conté: to_autor, recursos_literaris, reptes...
# resultat conté: traduccio, decisions_clau, avisos...
```

### Model de resultat

```python
ResultatTraduccio:
    traduccio: str           # Text traduït
    decisions_clau: list     # Justificacions de decisions
    termes_preservats: dict  # Com s'han traduït termes clau
    recursos_adaptats: list  # Com s'han adaptat recursos
    notes_traductor: list    # Notes [N.T.] generades
    confianca: float         # 0-1
    avisos: list             # Aspectes a revisar
```

### Flux recomanat

```
Text Original
     │
     ▼
AnalitzadorPreTraduccio ──► Anàlisi (to, recursos, reptes)
     │
     ▼
SelectorExemplesFewShot ──► Exemples similars
     │
     ▼
ContextTraduccioEnriquit ──► Context complet
     │
     ▼
TraductorEnriquit ──► Traducció + decisions
     │
     ▼
AvaluadorDimensional ──► Puntuació + feedback
     │
     ▼
(Si no aprovat) ──► Refinament iteratiu
```

---

## Refinador Iteratiu (v2)

### Concepte

El RefinadorIteratiu millora una traducció en un bucle:
1. Avalua amb AvaluadorDimensional
2. Si no aprovat, refina segons feedback prioritzat
3. Re-avalua
4. Repeteix fins a aprovació o màx iteracions

### Flux

```
Traducció inicial
       │
       ▼
   Avaluació ◄─────────────────┐
       │                       │
       ▼                       │
   Aprovat? ──► SÍ ──► FI     │
       │                       │
       NO                      │
       │                       │
       ▼                       │
   Refinament ─────────────────┘
   (max 3 iteracions)
```

### Ús bàsic

```python
from agents.v2 import RefinadorIteratiu

refinador = RefinadorIteratiu()

# Mètode simple: només retorna la traducció final
traduccio_final = refinador.refinar_fins_aprovacio(
    traduccio="Traducció literal...",
    text_original="Text original...",
    llengua_origen="japonès",
    genere="narrativa",
)
```

### Ús amb historial complet

```python
resultat = refinador.refinar(
    traduccio="Traducció inicial",
    text_original="Original",
    llengua_origen="llatí",
    autor="Sèneca",
    genere="filosofia",
)

print(resultat.traduccio_final)
print(resultat.aprovat)                # True/False
print(resultat.iteracions_realitzades) # 0, 1, 2, 3
print(resultat.millora_aconseguida)    # +1.5 punts
print(resultat.resum())                # Resum llegible

# Historial de cada iteració
for it in resultat.historial:
    print(f"Iteració {it.numero}: {it.dimensio_prioritzada}")
    print(f"  Canvis: {it.canvis_aplicats}")
```

### Llindars personalitzats

```python
from agents.v2.models import LlindarsAvaluacio

llindars = LlindarsAvaluacio(
    global_minim=7.5,          # Més permissiu
    veu_autor_minim=7.0,
    max_iteracions=5,          # Més iteracions
    llindar_revisio_humana=7.0,
)

refinador = RefinadorIteratiu(llindars=llindars)
```

### Refinador per dimensió

Per control més fi, refinar una dimensió específica:

```python
from agents.v2 import RefinadorPerDimensio

refinador_veu = RefinadorPerDimensio("veu_autor")
traduccio, canvis = refinador_veu.refinar(
    traduccio="Text...",
    text_original="Original...",
    feedback_dimensio="Recuperar el to irònic...",
)
```
