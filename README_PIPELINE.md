# 🏛️ Pipeline de Traducció de Textos Clàssics

Sistema complet de traducció automàtica de textos grecollatins al català amb control de qualitat.

## 🎯 Característiques

- ✅ **5 Agents especialitzats** integrats
- ✅ **Processament per chunks** per textos llargs
- ✅ **Glossari terminològic** automàtic
- ✅ **Revisió de qualitat** iterativa
- ✅ **Correcció ortogràfica** IEC
- ✅ **Control de costos** configurable
- ✅ **Pausa/represa** de sessions

## 🤖 Agents del Pipeline

```
┌─────────────────┐
│  ChunkerAgent   │  Divideix textos llargs
└────────┬────────┘
         ↓
┌─────────────────┐
│ GlossaristaAgent│  Genera glossari (opcional)
└────────┬────────┘
         ↓
    Per cada chunk:
         │
┌─────────────────┐
│ TranslatorAgent │  Tradueix grec/llatí → català
└────────┬────────┘
         ↓
┌─────────────────┐
│ ReviewerAgent   │  Revisa qualitat (N rondes)
└────────┬────────┘
         ↓
┌─────────────────┐
│ CorrectorAgent  │  Corregeix ortografia (opcional)
└────────┬────────┘
         ↓
    Fusió final
         ↓
┌─────────────────┐
│   📄 RESULTAT   │
└─────────────────┘
```

## 🚀 Ús Ràpid

```python
from pipeline.translation_pipeline import PipelineConfig, TranslationPipeline

# 1. Configurar
config = PipelineConfig(
    enable_glossary=True,
    enable_correction=True,
    max_revision_rounds=2,
)

# 2. Executar
pipeline = TranslationPipeline(config)
result = pipeline.run(
    text=text_grec,
    source_language="grec",
    author="Plató",
    work_title="El Banquet",
)

# 3. Resultats
print(f"Qualitat: {result.quality_score}/10")
print(f"Cost: €{result.total_cost_eur:.4f}")
```

## 📋 Tests

```bash
# Tests individuals dels agents
python test_integrated_pipeline.py agents

# Pipeline simple (text curt)
python test_integrated_pipeline.py simple

# Pipeline complet (text llarg amb chunking)
python test_integrated_pipeline.py chunked

# Exemple pràctic
python exemple_complet.py
```

## ⚙️ Configuració

### Opcions Principals

| Opció | Per Defecte | Descripció |
|-------|-------------|------------|
| `enable_glossary` | `True` | Activar generació de glossari |
| `enable_correction` | `True` | Activar correcció ortogràfica |
| `enable_chunking` | `True` | Dividir textos llargs |
| `max_revision_rounds` | `2` | Rondes màximes de revisió |
| `min_quality_score` | `7.0` | Puntuació mínima (1-10) |
| `correction_level` | `"normal"` | `relaxat` \| `normal` \| `estricte` |
| `cost_limit_eur` | `None` | Límit de cost (€) |

### Configuracions Recomanades

#### 🏃 Ràpida (econòmica)

```python
config = PipelineConfig(
    enable_glossary=False,
    enable_correction=False,
    max_revision_rounds=1,
    verbosity=VerbosityLevel.QUIET,
)
```

- **Cost**: ~50% menys
- **Temps**: Molt ràpid
- **Ús**: Esbossos, textos curts

#### ⚖️ Equilibrada (recomanada)

```python
config = PipelineConfig(
    enable_glossary=True,
    enable_correction=True,
    correction_level="normal",
    max_revision_rounds=2,
    min_quality_score=7.0,
    cost_limit_eur=5.0,
)
```

- **Cost**: Moderat
- **Qualitat**: Bona
- **Ús**: Producció general

#### 💎 Qualitat Màxima

```python
config = PipelineConfig(
    enable_glossary=True,
    enable_correction=True,
    correction_level="estricte",
    max_revision_rounds=3,
    min_quality_score=8.5,
    verbosity=VerbosityLevel.VERBOSE,
)
```

- **Cost**: Alt (~150%)
- **Qualitat**: Excel·lent
- **Ús**: Publicacions professionals

## 📊 Resultats

El `PipelineResult` conté:

```python
result.final_translation        # Traducció final
result.quality_score           # Puntuació 1-10
result.total_cost_eur          # Cost en EUR
result.total_tokens            # Tokens processats
result.chunk_results           # Resultats per chunk
result.accumulated_context     # Context acumulat
result.stages                  # Etapes executades
```

### Accedir al Glossari

```python
for term, entry in result.accumulated_context.glossary.items():
    print(f"{entry.term_original} → {entry.term_translated}")
```

### Revisar Correccions

```python
for chunk in result.chunk_results:
    corrections = chunk.metadata.get("corrections", [])
    for corr in corrections:
        print(f"{corr['tipus']}: {corr['original']} → {corr['corregit']}")
```

## 💰 Gestió de Costos

### Estimació per Agent

| Agent | Cost Relatiu | Freqüència |
|-------|--------------|------------|
| Glossarista | ~10% | 1 cop inicial |
| Traductor | ~60% | Per chunk |
| Revisor | ~25% | Per chunk × rondes |
| Corrector | ~15% | Per chunk |

### Optimitzar Costos

1. **Desactivar agents opcionals**:
   ```python
   enable_glossary=False  # -10%
   enable_correction=False  # -15%
   ```

2. **Reduir revisions**:
   ```python
   max_revision_rounds=1  # -50% del cost de revisió
   ```

3. **Afegir límit**:
   ```python
   cost_limit_eur=5.0  # Atura si supera €5
   ```

4. **Chunks més grans** (menys calls):
   ```python
   max_tokens_per_chunk=4000  # Més text per call
   ```

## 📁 Estructura de Fitxers

```
editorial-classica/
├── agents/
│   ├── __init__.py              # ← Actualitzat
│   ├── base_agent.py
│   ├── chunker_agent.py         # ✅
│   ├── glossarista.py           # ✅ (actualitzat)
│   ├── translator_agent.py      # ✅
│   ├── reviewer_agent.py        # ✅
│   └── corrector.py             # ✅ (actualitzat)
├── pipeline/
│   └── translation_pipeline.py  # ← Actualitzat amb tots els agents
├── utils/
│   ├── logger.py
│   └── dashboard.py
├── test_integrated_pipeline.py  # ← NOU (tests)
├── exemple_complet.py           # ← NOU (exemple)
├── RESUM_INTEGRACIO.md          # ← NOU (resum)
├── INTEGRACIO_AGENTS.md         # ← NOU (documentació tècnica)
└── README_PIPELINE.md           # ← Aquest fitxer
```

## 🔧 Troubleshooting

### Error: Agent no trobat

```python
# Assegura't que has importat correctament
from agents import ChunkerAgent, GlossaristaAgent, CorrectorAgent
```

### Error: JSON parsing failed

Augmenta la verbositat per veure l'error:

```python
config = PipelineConfig(verbosity=VerbosityLevel.DEBUG)
```

### Cost massa elevat

Activa el límit de cost:

```python
config = PipelineConfig(cost_limit_eur=2.0)
```

### Qualitat baixa

Augmenta les rondes de revisió:

```python
config = PipelineConfig(
    max_revision_rounds=3,
    min_quality_score=8.0,
)
```

## 📚 Documentació

- **[RESUM_INTEGRACIO.md](RESUM_INTEGRACIO.md)**: Resum executiu de la integració
- **[INTEGRACIO_AGENTS.md](INTEGRACIO_AGENTS.md)**: Documentació tècnica detallada
- **[exemple_complet.py](exemple_complet.py)**: Exemple pràctic amb comentaris

## 🎓 Exemples d'Ús

### 1. Traducció Simple

```python
from pipeline.translation_pipeline import PipelineConfig, TranslationPipeline

config = PipelineConfig(enable_chunking=False)
pipeline = TranslationPipeline(config)

result = pipeline.run(
    text="Ὁ βίος βραχύς, ἡ δὲ τέχνη μακρή",
    source_language="grec",
)
print(result.final_translation)
```

### 2. Llibre Complet

```python
# Llegir text
text = Path("sources/banquet_plato.txt").read_text()

# Configurar per text llarg
config = PipelineConfig(
    enable_chunking=True,
    max_tokens_per_chunk=3000,
    enable_glossary=True,
    cost_limit_eur=20.0,
)

# Processar
pipeline = TranslationPipeline(config)
result = pipeline.run(text, source_language="grec", work_title="El Banquet")

# Guardar
Path("output/banquet_traduit.txt").write_text(result.final_translation)
```

### 3. Revisar Només Glossari

```python
from agents import GlossaristaAgent, GlossaryRequest

glossarist = GlossaristaAgent()
response = glossarist.create_glossary(
    GlossaryRequest(
        text_original=text_grec,
        llengua_original="grec",
    )
)

import json
glossary = json.loads(response.content)
print(json.dumps(glossary, indent=2, ensure_ascii=False))
```

## 🌟 Funcionalitats Avançades

### Pausa i Represa

```python
# Primera sessió (es pausa)
pipeline = TranslationPipeline(config)
pipeline.request_pause()  # Pausar després del chunk actual
result = pipeline.run(text)

# Carregar estat
state = pipeline.load_state(Path(".cache/pipeline/state_20260125_143022.json"))

# Reprendre
result = pipeline.run(text, resume_from=state)
```

### Dashboard en Temps Real

```python
config = PipelineConfig(
    use_dashboard=True,  # Activar dashboard
    verbosity=VerbosityLevel.VERBOSE,
)
```

### Callbacks de Progrés

```python
def progress_callback(current, total, message):
    print(f"[{current}/{total}] {message}")

pipeline.set_progress_callback(progress_callback)
```

## 📈 Roadmap

- [x] Integrar ChunkerAgent
- [x] Integrar GlossaristaAgent
- [x] Integrar CorrectorAgent
- [ ] Afegir PerseusClient (validació de textos)
- [ ] Afegir FormatterAgent (EPUB/PDF)
- [ ] Cache persistent de glossari
- [ ] Tests unitaris per cada agent
- [ ] Benchmark de qualitat

## 🤝 Contribuir

Per afegir nous agents:

1. Crea `agents/nou_agent.py` heretant de `BaseAgent`
2. Afegeix-lo a `agents/__init__.py`
3. Integra'l al pipeline en `pipeline/translation_pipeline.py`
4. Actualitza aquesta documentació

## 📄 Llicència

Aquest projecte és part d'Editorial Clàssica.

---

✨ **Pipeline complet i funcional** • 📅 Gener 2026
