# Changelog

Tots els canvis notables del projecte.

## [2.4.0] - 2026-02-02

### Afegit
- **Correcció Normativa Automàtica**: LanguageTool ara aplica correccions dins del pipeline
- `agents/corrector_normatiu.py`: Nou agent de correcció normativa
- Configuració granular: `categories_auto` vs `categories_informe`
- Límit de seguretat per correccions per chunk (`max_correccions_chunk`)
- Tests complets per al corrector normatiu

### Millorat
- Pipeline V2 ara inclou pas de correcció normativa després del perfeccionament
- Avisos de gramàtica/estil per revisió humana (no corregits automàticament)
- `ResultatChunk` ara inclou `correccio_normativa` amb estadístiques detallades
- Nova fase `CORREGINT` a l'enum `FasePipeline`

### Flux actualitzat
```
Traductor → Revisor → Perfeccionament → Corrector Normatiu → Anotador
```

### Configuració
```python
ConfiguracioPipelineV2(
    fer_correccio_normativa=True,  # Activar/desactivar
    config_corrector=ConfiguracioCorrector(
        categories_auto=["ortografia", "tipografia", "puntuacio"],
        categories_informe=["gramatica", "estil", "barbarisme"],
        max_correccions_chunk=50,
    )
)
```

## [2.3.0] - 2026-01-30

### Afegit
- **LanguageTool integrat**: Correcció ortogràfica i gramatical automàtica
- `utils/corrector_linguistic.py`: Mòdul de correcció amb barbarismes extra
- Detecció de 40+ barbarismes castellans i anglesos
- Integració amb AvaluadorFluidesa (55% LLM + 25% calcs + 20% LanguageTool)
- Funció `corregir_traduccio_languagetool()` al post-processament

### Millorat
- Puntuació de fluïdesa ara inclou errors normatius
- Feedback més detallat amb suggeriments de correcció

## [2.2.0] - 2026-01-30

### Afegit
- **Detector de calcs multilingüe**: Patrons per rus, japonès, àrab, xinès, italià, portuguès
- Falsos amics per 10 llengües (rus, japonès, italià, portuguès, xinès, àrab + existents)
- Mètodes de detecció específics per cada família lingüística

### Millorat
- `_detectar_per_llengua()` ara suporta 12 llengües amb variants de nom
- Patrons de detecció més precisos per anglès (gerundi com a subjecte)
- Documentació de llengües suportades

## [2.1.0] - 2026-01-30

### Afegit
- **core/estat_pipeline.py**: Sistema de persistència d'estat per reprendre traduccions
- **core/memoria_contextual.py**: Memòria contextual per coherència entre chunks
- **core/validador_final.py**: Validador amb checklist complet abans de publicar
- **agents/investigador.py**: Agent Investigador per context històric i cultural
- **utils/detector_calcs.py**: Detector automàtic de calcs lingüístics
- **scripts/test_pipeline_complet.py**: Script de test d'integració complet
- **docs/ARQUITECTURA.md**: Documentació tècnica del sistema

### Millorat
- **TraductorEnriquit**: Ara usa context de MemoriaContextual per coherència
- **AvaluadorFluidesa**: Integra detector de calcs (70% LLM + 30% regex)
- **AnotadorCritic**: Usa notes pendents de l'investigador per anotacions informades
- **Pipeline V2**: Nova fase d'investigació abans del glossari
- **Dashboard**: S'atura automàticament quan la traducció es completa

### Corregit
- Fix `--tools ""` en base_agent.py per evitar error de max_turns amb CLI
- Fix validació de booleans (ok=None) en validador_final.py
- Fix signatura de portadista en script de test

### Tècnic
- Nou mòdul `core/` per components de persistència i validació
- Integració completa de MemoriaContextual amb Investigador, Traductor i Anotador
- Detecció automàtica de 14 tipus de calcs lingüístics
- Sistema de notes pendents [H]/[C]/[T] entre agents

## [1.0.0] - 2026-01-25

### Afegit
- Sistema web complet amb mode bilingue
- Enchiridion d'Epictetus (capitols 1-5) traduit
- Notes hiperlinkades amb retorn al text
- Glossari interactiu amb tooltips
- Mode clar/fosc
- Disseny responsive
- Pipeline de traduccio amb agents IA
- GitHub Pages per publicacio

### Primera versio publica!
