# Integració dels Agents al Pipeline

## Resum dels Canvis

S'han integrat **tots els agents** del projecte del Banquet de Plató al pipeline de traducció:

### Agents Integrats

1. **ChunkerAgent** ✅ (ja estava)
   - Divideix textos llargs en fragments òptims
   - Respecta l'estructura (TEI XML, Markdown, paràgrafs)
   - Detecta parlants i context

2. **GlossaristaAgent** ✅ (NOU)
   - Genera glossari terminològic inicial
   - Assegura consistència de traduccions
   - Identifica termes clau i noms propis

3. **TranslatorAgent** ✅ (ja estava)
   - Tradueix del grec/llatí al català
   - Utilitza el glossari per coherència
   - Manté l'estil literari

4. **ReviewerAgent** ✅ (ja estava)
   - Revisa la qualitat de la traducció
   - Identifica problemes i errors
   - Proposa millores

5. **CorrectorAgent** ✅ (NOU)
   - Corregeix ortografia i gramàtica
   - Aplica normativa IEC
   - Identifica barbarismes i calcs

## Flux del Pipeline

```
Text Original
     ↓
[1] CHUNKING - Dividir en fragments
     ↓
[2] GLOSSARI - Generar terminologia (només 1 cop)
     ↓
Per cada chunk:
  [3] TRADUCCIÓ - Traduir amb context
       ↓
  [4] REVISIÓ - Revisar qualitat (N rondes)
       ↓
  [5] CORRECCIÓ - Corregir ortografia
     ↓
[6] FUSIÓ - Unir tots els chunks
     ↓
Traducció Final
```

## Configuració

### Opcions Noves a `PipelineConfig`

```python
config = PipelineConfig(
    # Agents opcionals (default: True)
    enable_glossary=True,      # Activar GlossaristaAgent
    enable_correction=True,    # Activar CorrectorAgent
    correction_level="normal", # Nivell: relaxat|normal|estricte

    # Configuració existent
    enable_chunking=True,
    max_tokens_per_chunk=3500,
    max_revision_rounds=2,
    min_quality_score=7.0,
)
```

## Ús

### Test Individual dels Agents

```bash
python test_integrated_pipeline.py agents
```

### Test Pipeline Simple (sense chunking)

```bash
python test_integrated_pipeline.py simple
```

### Test Pipeline Complet (amb chunking)

```bash
python test_integrated_pipeline.py chunked
```

### Exemple de Codi

```python
from pipeline.translation_pipeline import PipelineConfig, TranslationPipeline
from utils.logger import VerbosityLevel

# Configurar pipeline
config = PipelineConfig(
    enable_chunking=True,
    enable_glossary=True,
    enable_correction=True,
    correction_level="normal",
    max_revision_rounds=2,
    verbosity=VerbosityLevel.NORMAL,
)

# Crear pipeline
pipeline = TranslationPipeline(config)

# Executar
result = pipeline.run(
    text=text_grec,
    source_language="grec",
    author="Plató",
    work_title="El Banquet",
)

# Mostrar resultats
pipeline.display_result(result)
```

## Etapes del Pipeline

### PipelineStage (enums actualitzats)

```python
class PipelineStage(str, Enum):
    PENDING = "pendent"
    CHUNKING = "seccionant"
    GLOSSARY = "glossariant"     # ← NOU
    TRANSLATING = "traduint"
    REVIEWING = "revisant"
    REFINING = "refinant"
    CORRECTING = "corregint"     # ← NOU
    MERGING = "fusionant"
    COMPLETED = "completat"
    FAILED = "fallat"
    PAUSED = "pausat"
```

## Metadades del Resultat

El `PipelineResult` ara inclou:

```python
result.stages                  # Totes les etapes executades
result.chunk_results          # Resultats per chunk
result.accumulated_context    # Context acumulat (glossari, etc.)
result.quality_score          # Puntuació mitjana
result.total_cost_eur         # Cost total en EUR
result.total_tokens           # Tokens processats
```

### Informació de Correccions

```python
for chunk in result.chunk_results:
    corrections = chunk.metadata.get("corrections", [])
    corrections_count = chunk.metadata.get("corrections_count", 0)
```

### Glossari Generat

```python
for term_key, entry in result.accumulated_context.glossary.items():
    print(f"{entry.term_original} → {entry.term_translated}")
```

## Gestió de Costos

El pipeline integrat pot tenir un cost més elevat degut als agents addicionals:

- **Glossarista**: ~1 crida inicial (mostra del text)
- **Corrector**: 1 crida per chunk

Per limitar costos:

```python
config = PipelineConfig(
    enable_glossary=False,     # Desactivar glossari
    enable_correction=False,   # Desactivar correcció
    cost_limit_eur=5.0,       # Límit de cost
)
```

## Fitxers Modificats

1. `agents/__init__.py` - Exportar nous agents
2. `pipeline/translation_pipeline.py` - Integrar agents al flux
3. `test_integrated_pipeline.py` - Tests de verificació (NOU)
4. `INTEGRACIO_AGENTS.md` - Aquesta documentació (NOU)

## Notes Tècniques

### Context Acumulat

El `AccumulatedContext` ara s'emplena amb:

- **Glossari inicial**: Generat pel GlossaristaAgent
- **Termes actualitzats**: Per cada chunk processat
- **Parlants**: Detectats pel ChunkerAgent
- **Resums**: Context dels chunks anteriors

### Ordre d'Execució per Chunk

1. **Traducció** amb context (glossari + resums anteriors)
2. **Revisió** iterativa (màx N rondes) fins qualitat >= llindar
3. **Correcció** ortogràfica/gramatical (IEC)
4. **Actualització** del context acumulat

### PerseusClient

**Nota**: L'usuari va mencionar "possiblement PerseusClient" però no s'ha trobat
implementat al codi. Si existeix o es vol afegir, caldrà:

- Crear `utils/perseus_client.py` o similar
- Integrar-lo al ChunkerAgent o com a validador del text original
- Afegir-lo als imports i configuració

## TODOs Futurs

- [ ] Afegir FormatterAgent per generar EPUB/PDF
- [ ] Implementar PerseusClient per validar textos
- [ ] Optimitzar cost: cache de glossari entre sessions
- [ ] Afegir tests unitaris per cada agent
- [ ] Documentar millor les metadades de cada etapa
