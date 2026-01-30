# Changelog

Tots els canvis notables del projecte.

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
