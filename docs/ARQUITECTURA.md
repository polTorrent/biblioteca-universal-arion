# Arquitectura del Sistema de Traducció

## Visió General

El sistema de traducció de la Biblioteca Universal Arion utilitza una arquitectura basada en agents especialitzats que col·laboren per produir traduccions literàries de qualitat acadèmica.

```
┌─────────────────────────────────────────────────────────────────┐
│                        PIPELINE V2                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │ Investigador │───▶│  Glossarista │───▶│   Chunker    │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                   │                   │                │
│         ▼                   ▼                   ▼                │
│  ┌─────────────────────────────────────────────────────┐        │
│  │              MEMÒRIA CONTEXTUAL                      │        │
│  │  - Context investigació (autor, obra, temes)         │        │
│  │  - Traduccions registrades (glossari coherent)       │        │
│  │  - Notes pendents (personatges, referències)         │        │
│  └─────────────────────────────────────────────────────┘        │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   PER CADA CHUNK                          │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐          │   │
│  │  │ Analitzador│─▶│ Traductor  │─▶│ Avaluador  │          │   │
│  │  └────────────┘  └────────────┘  └────────────┘          │   │
│  │                         │              │                  │   │
│  │                         ▼              ▼                  │   │
│  │                  ┌────────────┐  ┌────────────┐          │   │
│  │                  │ Refinador  │◀─│  Detector  │          │   │
│  │                  │ Iteratiu   │  │   Calcs    │          │   │
│  │                  └────────────┘  └────────────┘          │   │
│  └──────────────────────────────────────────────────────────┘   │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Validador  │───▶│   Anotador   │───▶│  Publisher   │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Components Core

### EstatPipeline (`core/estat_pipeline.py`)

Gestiona la persistència de l'estat del pipeline per permetre reprendre traduccions interrompudes.

```python
from core import EstatPipeline

# Iniciar o reprendre
estat = EstatPipeline(directori_obra=Path("obres/plato/apologia"))

if estat.existeix():
    estat.carregar()
    chunks_pendents = estat.obtenir_chunks_pendents()
else:
    estat.iniciar_fase("glossari")
    # ... processar
    estat.completar_fase("glossari")
    estat.guardar()
```

**Característiques:**
- Guarda estat a `.pipeline_state.json`
- Registra fases completades i chunks processats
- Permet reprendre des de qualsevol punt
- Auto-guarda després de cada canvi

### MemoriaContextual (`core/memoria_contextual.py`)

Manté coherència entre chunks i proporciona context als agents.

```python
from core import MemoriaContextual, ContextInvestigacio

memoria = MemoriaContextual()

# Establir context d'investigació
memoria.establir_context_investigacio(ContextInvestigacio(
    autor_bio="Plató (428-348 aC)...",
    context_historic="Grècia clàssica...",
    temes_principals=["justícia", "virtut"],
))

# Registrar traduccions per coherència
memoria.registrar_traduccio("σοφία", "saviesa", "Terme filosòfic", "chunk_1")

# Afegir notes per l'anotador
memoria.afegir_nota_pendent("[H] Personatge: Sòcrates")

# Generar context per al traductor
context = memoria.generar_context_per_traductor()
```

**Característiques:**
- Emmagatzema context d'investigació
- Manté glossari de traduccions coherent
- Guarda notes pendents per l'anotador
- Exportable/importable amb estat del pipeline

### ValidadorFinal (`core/validador_final.py`)

Checklist complet abans de publicar una obra.

```python
from core import ValidadorFinal

validador = ValidadorFinal(directori_obra=Path("obres/plato/apologia"))
resultat = validador.validar()

if resultat.pot_publicar:
    print("Obra llesta per publicar!")
else:
    print(resultat.generar_informe())
```

**Categories de validació:**
- Fitxers obligatoris (original.md, traduccio.md, metadata.yml)
- Metadades (autor, títol, llengua, estat)
- Contingut (longitud mínima, introducció)
- Notes i glossari (format, coherència)
- Portada (existència)

---

## Agents de Traducció

### InvestigadorAgent (`agents/investigador.py`)

Recull context històric i cultural abans de traduir.

```python
from agents.investigador import investigar_obra

informe = investigar_obra(
    autor="Plató",
    obra="Apologia de Sòcrates",
    llengua="grec antic",
    memoria=memoria,  # Guarda resultats automàticament
)

print(informe.autor_bio_breu)
print(informe.obra_temes_principals)
print(informe.personatges_mencions)  # Per l'anotador
```

**Sortida:**
- Biografia de l'autor
- Context històric i literari
- Temes principals de l'obra
- Personatges, referències, termes tècnics (notes pendents)

### TraductorEnriquit (`agents/v2/traductor_enriquit.py`)

Traductor que utilitza context enriquit per a traduccions literàries.

```python
from agents.v2.traductor_enriquit import TraductorEnriquit
from agents.v2.models import ContextTraduccioEnriquit

traductor = TraductorEnriquit()
context = ContextTraduccioEnriquit(
    text_original="...",
    llengua_origen="grec",
    autor="Plató",
    analisi=analisi_previa,
    glossari=glossari,
)

resultat = traductor.traduir(context, memoria)  # Usa context de memòria
```

**Característiques:**
- Rep anàlisi prèvia del text
- Incorpora exemples few-shot
- Usa context de MemoriaContextual
- Documenta decisions de traducció

### AvaluadorDimensional (`agents/v2/avaluador_dimensional.py`)

Sistema d'avaluació en 3 dimensions ortogonals.

```python
from agents.v2.avaluador_dimensional import AvaluadorDimensional

avaluador = AvaluadorDimensional()
feedback = avaluador.avaluar_rapid(
    text_original="...",
    text_traduit="...",
    llengua_origen="grec",
)

print(f"Fidelitat: {feedback.puntuacio_fidelitat}/10")
print(f"Veu autor: {feedback.puntuacio_veu_autor}/10")
print(f"Fluïdesa: {feedback.puntuacio_fluidesa}/10")
print(f"Aprovat: {feedback.aprovat}")
```

**Dimensions:**
1. **Fidelitat** - El significat es preserva?
2. **Veu de l'autor** - El to i estil es mantenen?
3. **Fluïdesa** - Sona natural en català?

**Integració amb DetectorCalcs:**
- Detecció automàtica de calcs (regex)
- Puntuació combinada: 70% LLM + 30% detector

### AnotadorCriticAgent (`agents/anotador_critic.py`)

Afegeix notes erudites informades per l'investigador.

```python
from agents.anotador_critic import AnotadorCriticAgent, AnotacioRequest

anotador = AnotadorCriticAgent()
request = AnotacioRequest(
    text="...",
    llengua_origen="grec",
    densitat_notes="normal",
)

response = anotador.annotate(request, memoria)  # Usa notes pendents
```

**Tipus de notes:**
- [H] Històriques/prosopogràfiques
- [C] Culturals
- [T] Terminològiques
- Intertextuals, geogràfiques, textuals

---

## Utilitats

### DetectorCalcs (`utils/detector_calcs.py`)

Detecta construccions no naturals en català.

```python
from utils.detector_calcs import detectar_calcs

resultat = detectar_calcs(
    "Dit això, el rei marxà. Certament era noble.",
    llengua_origen="llatí"
)

print(f"Fluïdesa: {resultat.puntuacio_fluidesa}/10")
for calc in resultat.calcs:
    print(f"  {calc.tipus}: {calc.text_original}")
    print(f"    → {calc.suggeriment}")
```

**Tipus de calcs detectats:**
- Ablatius absoluts ("Dit això")
- Connectors llatinitzants ("Certament", "No obstant això")
- Passives excessives
- Gerundis anglesos
- Verbs al final (alemany)
- Falsos amics
- Pronoms redundants

---

## Pipeline V2

### Configuració

```python
from agents.v2 import PipelineV2, ConfiguracioPipelineV2

config = ConfiguracioPipelineV2(
    # Investigació (NOU)
    fer_investigacio=True,

    # Anàlisi
    fer_analisi_previa=True,
    usar_exemples_fewshot=True,

    # Glossari i chunking
    crear_glossari=True,
    fer_chunking=True,
    max_chars_chunk=3000,

    # Avaluació
    fer_avaluacio=True,
    fer_refinament=True,

    # Persistència (NOU)
    habilitar_persistencia=True,
    directori_obra=Path("obres/autor/obra"),

    # Validació (NOU)
    habilitar_validacio_final=True,
    bloquejar_si_invalid=True,

    # Dashboard
    mostrar_dashboard=True,
)

pipeline = PipelineV2(config=config)
```

### Flux d'Execució

```
0. INVESTIGACIÓ (NOU)
   └─▶ InvestigadorAgent → context a MemoriaContextual

1. GLOSSARI
   └─▶ GlossaristaAgent → termes a MemoriaContextual

2. CHUNKING
   └─▶ ChunkerAgent → divisió en fragments

3. PER CADA CHUNK:
   a. Anàlisi Pre-Traducció
   b. Traducció Enriquida (amb memòria)
   c. Avaluació Dimensional (amb detector calcs)
   d. Refinament Iteratiu (si cal)

4. FUSIÓ
   └─▶ Combinar chunks traduïts

5. VALIDACIÓ FINAL (NOU)
   └─▶ ValidadorFinal → checklist complet

6. POST-PROCESSAMENT
   └─▶ Portades, EPUB, publicació web
```

### Reprendre Traducció

```python
# Reprendre una traducció interrompuda
pipeline = PipelineV2.reprendre(
    directori_obra=Path("obres/plato/apologia")
)

# Continua des d'on es va quedar
resultat = pipeline.traduir(
    text=text_original,
    autor="Plató",
    obra="Apologia de Sòcrates",
)
```

---

## Autenticació

### Model Dual

```python
# Claude Code (subscripció) - cost €0
os.environ["CLAUDECODE"] = "1"
# Els agents detecten automàticament i usen CLI

# Usuaris web (API) - pay-per-token
config = AgentConfig(use_api=True)
# Usa SDK d'Anthropic
```

**Regla obligatòria per scripts:**
```python
#!/usr/bin/env python3
import os
os.environ["CLAUDECODE"] = "1"  # ABANS d'importar agents!

from agents.v2 import PipelineV2
```

---

## Dashboard

El dashboard web mostra el progrés en temps real:

```python
from dashboard import start_dashboard

dash = start_dashboard(
    obra="Apologia de Sòcrates",
    autor="Plató",
    llengua="grec"
)

# S'obre automàticament al navegador
# URL: http://127.0.0.1:5050
```

**Característiques:**
- Progrés per chunks
- Logs en temps real
- Mètriques de qualitat
- Temps transcorregut
- S'atura automàticament en completar

---

## Estructura de Fitxers

```
biblioteca-universal-arion/
├── agents/
│   ├── v2/
│   │   ├── pipeline_v2.py      # Orquestrador principal
│   │   ├── traductor_enriquit.py
│   │   ├── avaluador_dimensional.py
│   │   ├── analitzador_pre.py
│   │   └── refinador_iteratiu.py
│   ├── investigador.py         # NOU: Context històric
│   ├── anotador_critic.py
│   ├── glossarista.py
│   └── chunker_agent.py
├── core/
│   ├── estat_pipeline.py       # NOU: Persistència
│   ├── memoria_contextual.py   # NOU: Coherència
│   └── validador_final.py      # NOU: Validació
├── utils/
│   ├── detector_calcs.py       # NOU: Detecció calcs
│   └── logger.py
├── dashboard/
│   ├── server.py
│   └── templates/
└── scripts/
    └── test_pipeline_complet.py
```

---

## Mètriques de Qualitat

| Mètrica | Llindar Mínim | Objectiu |
|---------|---------------|----------|
| Fidelitat | 6.0 | 8.0+ |
| Veu Autor | 6.5 | 8.0+ |
| Fluïdesa | 6.0 | 8.0+ |
| Global | 7.0 | 8.0+ |
| Fiabilitat Investigació | - | 8.0+ |

---

*Documentació generada: 2026-01-30*
