# Biblioteca Universal Arion — Projecte

## Què és
Biblioteca digital de clàssics universals traduïts al català. Sistema autònom que gestiona descobriment, obtenció de fonts, traducció, validació i publicació.

## Stack
- **Bash**: Heartbeat, workers, automatització
- **Python**: Traducció (Venice AI), task manager, web builder
- **Venice AI**: Model d'inferència (GLM 5.1, Claude, etc.)
- **Hermes**: Agent coordinador
- **GitHub Pages**: Publicació web

## Convenis
- Idioma: Català
- Mode: CONSOLIDACIÓ (qualitat > quantitat, mai <7/10)
- Mínim DIEM: 3.0 (worker atura si <3)
- Commit per tasca (no batch)
- No generar obres noves en mode consolidació

## Estructura clau
```
sistema/automatitzacio/heartbeat.sh  → Orchestrador
sistema/automatitzacio/worker.sh      → Worker unificat
sistema/automatitzacio/modules/       → 10 mòduls del heartbeat
sistema/automatitzacio/notificar.sh   → Notificacions unificades
sistema/scripts/task_manager.py       → Task manager Python
sistema/scripts/check_*.py            → Scripts anàlisi
sistema/config/models.conf            → Configuració models
sistema/tasks/{pending,running,done,failed}/ → Cua de tasques
sistema/state/                        → Estat del sistema
obres/                                → Les obres traduides
```

## Prohibicions
- No generar obres noves en mode consolidació
- No modificar obres validades sense .needs_fix
- No aturar el worker sense graceful shutdown
- No commit sense missatge descriptiu

## Sistema d'audiollibres
Generació d'audiollibres amb Venice TTS (model tts-elevenlabs-turbo-v2-5).

### Comandes ràpides
```bash
# Generar audiollibre d'una obra validada
python3 scripts/generar_audiollibre.py obres/filosofia/seneca/epistola-1/

# Amb veu específica
python3 scripts/generar_audiollibre.py obres/filosofia/seneca/epistola-1/ --voice George

# Forçar regeneració
python3 scripts/generar_audiollibre.py obres/filosofia/seneca/epistola-1/ --force

# Només capítols o només complet
python3 scripts/generar_audiollibre.py obres/narrativa/kafka/metamorfosi/ --capitols-nomes
python3 scripts/generar_audiollibre.py obres/narrativa/kafka/metamorfosi/ --complet-nomes
```

### Components
- **Agent Narrador**: `sistema/traduccio/agents/narrador.py` — Agent principal
- **Client Venice TTS**: `sistema/traduccio/agents/venice_client.py` — Mètodes TTS
- **Script**: `scripts/generar_audiollibre.py` — CLI per generar audiollibres

### Mapatge veus per gènere
| Gènere | Veu |
|--------|-----|
| filosofia | George |
| narrativa | Charlie |
| poesia | Charlotte |
| teatre | Adam |
| oriental | Laura |
| assaig | Daniel |

### Sortida
Cada obra amb audiollibre genera:
- `obres/[cat]/[autor]/[obra]/audio/audiollibre_complet.mp3`
- `obres/[cat]/[autor]/[obra]/audio/capitol_XX.mp3` (si té capítols)
- `obres/[cat]/[autor]/[obra]/audio/manifest.json`
- Camp `audiobook:` afegit a `metadata.yml`
