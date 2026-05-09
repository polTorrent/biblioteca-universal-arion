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
