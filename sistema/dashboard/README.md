# Arion Dashboard - Sistema de Monitorització en Temps Real

## 📊 Visió General

Dashboard professional per monitorar totes les activitats del sistema Arion en temps real:
- **Pensament d'Hermes** - Raonament i decisions de l'agent
- **Thinking dels LLM** - Pensament dels models Venice
- **Tool Calls** - Crides a funcions
- **Worker Log** - Activitat del worker automàtic
- **Errors** - Errors i exceptions

## 🚀 Arrencada Ràpida

### 1. Arrencar el Dashboard

```bash
cd ~/biblioteca-universal-arion/sistema/dashboard
./start.sh
```

O manualment:

```bash
cd ~/biblioteca-universal-arion/sistema/dashboard
python3 server.py
```

### 2. Accedir al Dashboard

- **Local**: http://localhost:9120
- **TailScale**: http://100.93.26.104:9120

### 3. Enviar Events

Des de qualsevol script o terminal:

```bash
# Des de Python
python3 logger.py hermes "Analitzant tasca nova..."

# Des de Bash
./log-to-dashboard.sh worker "Iniciant traducció de De Anima"
```

## 📝 Tipus d'Events

| Tipus | Fitxer | Descripció |
|-------|--------|------------|
| `hermes` | `logs/hermes.log` | Pensament i decisions d'Hermes |
| `llm` | `logs/llm.log` | Thinking dels models LLM (Venice) |
| `worker` | `logs/worker.log` | Logs del worker automàtic |
| `tools` | `logs/tools.log` | Crides a eines (terminal, patch, etc.) |
| `error` | `logs/errors.log` | Errors i exceptions |

## 🔧 Integració amb el Worker

### Opció 1: Logging Manual (Fàcil)

Afegir crides a `logger.py` als scripts:

```python
import subprocess

def log_to_dashboard(event_type, message):
    subprocess.run(['python3', 'logger.py', event_type, message])

# Ús
log_to_dashboard('worker', f"Processant tasca: {tasca_id}")
log_to_dashboard('llm', thinking_output)
log_to_dashboard('error', f"Error: {str(e)}")
```

### Opció 2: Wrapper Automàtic (Recomanat)

Utilitzar el wrapper que captura tot l'output:

```bash
# En lloc de:
python3 traduir_venice.py "grec" "catala" "text"

# Utilitzar:
./wrapper-with-logging.sh python3 traduir_venice.py "grec" "catala" "text"
```

### Opció 3: Intgració Hermes (Avançat)

Modificar el sistema Hermes per enviar events automàticament.

## 📦_APIs

### GET `/api/status`

Retorna l'estat actual del sistema:

```json
{
  "worker": {
    "running": true,
    "pid": 12345,
    "uptime": 3600
  },
  "venice": {
    "diem": 14.97,
    "requests": 149,
    "tokens": 3000000
  },
  "queue": {
    "count": 3
  }
}
```

### GET `/api/events/{type}`

Retorna els últims 50 events d'un tipus específic.

### GET `/api/events/all`

Retorna tots els events recents.

## 🎨 Personalització

### Modificar Colors

Edita `static/style.css` i canvia les variables CSS:

```css
:root {
    --accent-blue: #4a9eff;
    --accent-green: #00d26a;
    --accent-yellow: #ffc107;
    --accent-red: #ff4757;
}
```

### Afegir Panells

1. Afegir HTML a `static/index.html`
2. Afegir CSS a `static/style.css`
3. Actualitzar `server.py` per enviar events nous

## 🔍 Depuració

### Veure Logs en Temps Real

```bash
# Hermes
tail -f logs/hermes.log

# LLM
tail -f logs/llm.log

# Worker
tail -f logs/worker.log

# Tools
tail -f logs/tools.log

# Errors
tail -f logs/errors.log

# Dashboard server
tail -f logs/dashboard.log
```

### Aturar el Dashboard

```bash
pkill -f "python3 server.py"
```

## 📊 Status Actual

El dashboard mostra en temps real:
- ✅ **Estat del Worker**: Actiu/Aturat amb PID
- ✅ **Balance DIEM**: Crèdits disponibles Venice
- ✅ **Requests Venice**: Requests restants
- ✅ **Tokens Venice**: Tokens restants
- ✅ **Cua Tasques**: Nombre de tasques pendents

## 🔐 Seguretat

- El dashboard corre en localhost (8888)
- Accessible via TailScale (xarxa privada)
- No exposat a internet públic
- Logs en fitxers locals

## 🚧 Pròxims Passos

1. [ ] Integrar automàticament amb el worker
2. [ ] Capturar thinking dels LLM automàticament
3. [ ] Afegir gràfics de mètriques
4. [ ] Implementar alertes per errors
5. [ ] Afegir históric d'events (database)

## 📚 Documentació Relacionada

- `server.py` - Servidor Flask + WebSocket
- `logger.py` - Script per enviar events
- `wrapper-with-logging.sh` - Wrapper per capturar output
- `static/` - Fitxers HTML/CSS/JS del frontend