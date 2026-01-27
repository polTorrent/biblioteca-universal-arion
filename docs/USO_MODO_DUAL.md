# Guia d'Ús: Mode Dual (Subscripció vs API)

## Resum Ràpid

Els agents de la Biblioteca Arion funcionen en **mode dual**:

| Context | Autenticació | Cost | Exemple d'ús |
|---------|--------------|------|--------------|
| 🤖 **Claude Code** | Subscripció Pro/Max | €0 (fix mensual) | Traduccions internes |
| 🌐 **Usuaris web** | API d'Anthropic | Pay-per-token | Traduccions sota demanda |

La detecció és **automàtica** via variable d'entorn `CLAUDECODE=1`.

## Ús Normal (Mode Subscripció)

Quan executes traduccions des de Claude Code, **no cal fer res especial**. El sistema detecta automàticament que estàs en mode subscripció:

```python
from agents import TranslatorAgent, TranslationRequest

# Crear agent (detecta automàticament mode subscripció)
agent = TranslatorAgent()

# Traduir
request = TranslationRequest(
    text="こんにちは",
    source_language="japonès",
    author="Akutagawa",
    work_title="Jigokuhen",
)

response = agent.translate(request)

# Cost = €0.00 (subscripció)
print(f"Cost: €{response.cost_eur:.2f}")  # €0.00
```

## Forçar Mode API

Si necessites **forçar l'ús de l'API** (per exemple, per testejar el mode usuaris web):

```python
from agents import TranslatorAgent, AgentConfig

# Configurar amb use_api=True
config = AgentConfig(use_api=True)
agent = TranslatorAgent(config=config)

# Ara usarà l'API d'Anthropic (pagaràs per tokens)
response = agent.translate(request)

# Cost > €0 (API)
print(f"Cost: €{response.cost_eur:.4f}")  # €0.0248 per exemple
```

## Pipeline de Traducció

El `TranslationPipeline` també detecta automàticament el mode:

```python
from pipeline.translation_pipeline import TranslationPipeline, PipelineConfig

# Mode subscripció (automàtic en Claude Code)
config = PipelineConfig(
    enable_perfeccionament=True,
    # ... altres opcions
)

pipeline = TranslationPipeline(config=config)
result = pipeline.run(text="...", source_language="japonès")

# Tot el pipeline usarà subscripció (cost €0)
print(f"Cost total: €{result.total_cost_eur:.2f}")  # €0.00
```

## Verificar Mode Actiu

Pots verificar quin mode està actiu:

```python
agent = TranslatorAgent()

if agent.use_subscription:
    print("✅ Mode subscripció actiu (cost €0)")
else:
    print("💳 Mode API actiu (cost per token)")
```

## Logs

Quan executes traduccions, veuràs al log quin mode s'està utilitzant:

**Mode Subscripció:**
```
🌍 [Traductor] ✅ Mode subscripció actiu - usant claude CLI
✅ [Traductor] Completat (11.5s), tokens_in=3, tokens_out=95, cost=€0.0000
```

**Mode API:**
```
🌍 [Traductor] Processant...
✅ [Traductor] Completat (15.2s), tokens_in=3, tokens_out=95, cost=€0.0024
```

## Tests

### Test Unitari

```bash
python3 /tmp/claude/.../test_subscripcio.py
```

### Test Manual

```bash
# Mode subscripció (automàtic)
python3 scripts/traduir_obra.py --obra test

# Mode API (forçat)
FORCE_API=1 python3 scripts/traduir_obra.py --obra test
```

## Preguntes Freqüents

### P: Com sé si estic usant subscripció o API?

**R:** Mira el log. Si veus "✅ Mode subscripció actiu" i `cost=€0.0000`, estàs usant subscripció.

### P: He traduït Jigokuhen i m'ha costat €0.98, per què?

**R:** Probablement has executat abans de la implementació del mode dual (27/01/2026). Ara ja no passarà si executes des de Claude Code.

### P: Puc usar subscripció fora de Claude Code?

**R:** No. El mode subscripció només funciona dins de Claude Code (quan `CLAUDECODE=1`). Fora, sempre s'usa API.

### P: Els usuaris web pagaran més?

**R:** Els usuaris web paguen el cost real de l'API d'Anthropic (pay-per-token). És el model de negoci previst per a usuaris externs.

### P: Puc desactivar el mode subscripció?

**R:** Sí, passa `use_api=True` a `AgentConfig`:

```python
config = AgentConfig(use_api=True)
agent = TranslatorAgent(config=config)
```

## Detalls Tècnics

### Detecció Automàtica

```python
import os

is_claude_code = os.getenv("CLAUDECODE") == "1"

if is_claude_code and not config.use_api:
    # Usar subscripció (claude CLI)
    use_subscription = True
else:
    # Usar API
    use_subscription = False
```

### Crida al CLI

Internament, quan s'usa subscripció, els agents criden:

```bash
claude --print \
  --output-format json \
  --system-prompt "..." \
  --model claude-sonnet-4-20250514 \
  --no-session-persistence \
  "Prompt aquí"
```

### Format de Resposta

El CLI retorna:

```json
{
  "type": "result",
  "result": "Traducció aquí...",
  "usage": {
    "input_tokens": 3,
    "output_tokens": 95
  },
  "modelUsage": {
    "claude-sonnet-4-5-20250929": {...}
  }
}
```

## Històric

- **2026-01-27**: Implementació mode dual completada
- **Abans 2026-01-27**: Tots els agents usaven API (cost €0.98 per Jigokuhen)
- **Ara**: Mode subscripció per defecte en Claude Code (cost €0.00)

---

Per més detalls tècnics, consulta `docs/IMPLEMENTACIO_SUBSCRIPCIO.md`.
