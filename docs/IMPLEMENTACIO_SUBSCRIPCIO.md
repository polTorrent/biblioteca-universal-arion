# Implementació Mode Subscripció per Claude Code

## Problema Actual

Els agents (`BaseAgent`) actualment utilitzen l'SDK d'Anthropic (`anthropic.Anthropic()`) que consumeix **crèdits API** independentment del context.

Això és incorrecte per a l'ús intern de Claude Code, que hauria d'utilitzar la **subscripció Claude Pro/Max** (cost fix mensual).

## Objectiu

Implementar un **model dual**:

| Context | Autenticació | Cost | Ús |
|---------|--------------|------|-----|
| 🤖 Claude Code | Subscripció Pro/Max | Fix mensual ($20-200) | Desenvolupament intern, traduccions pròpies |
| 🌐 Usuaris web | API Anthropic | Pay-per-token | Usuaris externs que paguen per traducció |

## Detecció Automàtica

```python
import os

is_claude_code = os.getenv("CLAUDECODE") == "1"

if is_claude_code:
    # Usar subscripció
    pass
else:
    # Usar API
    client = anthropic.Anthropic()
```

## Opcions d'Implementació

### Opció 1: Subprocess al CLI `claude`

```python
import subprocess
import json

def call_claude_cli(prompt: str, system: str) -> str:
    """Crida a claude CLI amb subscripció."""
    result = subprocess.run(
        ["claude", "chat", "--message", prompt, "--system", system],
        capture_output=True,
        text=True,
    )
    return result.stdout
```

**Pros:**
- Utilitza directament la subscripció
- No requereix canvis a l'SDK

**Contras:**
- Més lent (overhead de subprocess)
- Més difícil gestionar streaming
- Parsing de la sortida manual

### Opció 2: SDK amb Suport Subscripció (si existeix)

```python
# Comprovar si l'SDK d'Anthropic suporta subscripcions
# Documentació: https://docs.anthropic.com/

client = anthropic.Anthropic(
    auth_type="subscription"  # Si aquesta opció existeix
)
```

**Pros:**
- API consistent
- Fàcil de mantenir

**Contras:**
- Pot no existir (cal verificar documentació)

### Opció 3: Proxy/Wrapper Intern

Crear un wrapper que:
1. Detecta context (Claude Code vs Web)
2. Redirigeix a subscripció o API segons context
3. Manté API consistent per a la resta del codi

```python
class ClaudeClient:
    def __init__(self):
        self.is_claude_code = os.getenv("CLAUDECODE") == "1"
        if not self.is_claude_code:
            self.api_client = anthropic.Anthropic()

    def messages_create(self, **kwargs):
        if self.is_claude_code:
            return self._call_via_subscription(**kwargs)
        else:
            return self.api_client.messages.create(**kwargs)

    def _call_via_subscription(self, **kwargs):
        # Implementar crida via subscripció
        pass
```

## Estat Actual del Codi

**Fitxer:** `agents/base_agent.py`

**Implementat:**
- ✅ Detecció de context (`CLAUDECODE=1`)
- ✅ Variable `use_subscription` per indicar mode
- ✅ Warning automàtic quan s'usa API en context incorrecte

**Pendent:**
- ❌ Implementació real de crides via subscripció
- ❌ Tests per validar ambdós modes
- ❌ Documentació d'ús per desenvolupadors

## Tasques Pendents

1. **Investigar SDK Anthropic**
   - Comprovar si suporta subscripcions directament
   - Revisar documentació oficial

2. **Implementar Opció Escollida**
   - Si SDK ho suporta → Opció 2
   - Altrament → Opció 1 (subprocess) o Opció 3 (wrapper)

3. **Actualitzar BaseAgent**
   - Eliminar el fallback temporal a API
   - Implementar lògica real de subscripció

4. **Tests**
   - Test en context Claude Code (subscripció)
   - Test en context web (API)
   - Validar costs calculats correctament

5. **Documentació**
   - Actualitzar CLAUDE.md
   - Afegir exemples d'ús
   - Documentar configuració

## Validació

Després d'implementar, validar:

```bash
# En Claude Code (hauria d'usar subscripció)
CLAUDECODE=1 python scripts/traduir_obra.py

# Verificar logs:
# → Ha de dir "Mode subscripció activat"
# → NO ha de dir "Using Anthropic API"

# En context web (hauria d'usar API)
unset CLAUDECODE
python scripts/traduir_obra.py

# Verificar logs:
# → Ha de dir "Using Anthropic API"
```

## Referències

- [Documentació Anthropic API](https://docs.anthropic.com/)
- [Claude Code CLI](https://github.com/anthropics/claude-code)
- `agents/base_agent.py` (codi actual)

---

**Data:** 2026-01-27
**Estat:** ✅ COMPLETAT
**Prioritat:** Alta (evitar costs innecessaris d'API)

## ✅ IMPLEMENTACIÓ COMPLETADA

**Data completat:** 2026-01-27

**Opció escollida:** Opció 1 - Subprocess al CLI `claude`

**Fitxers modificats:**
- `agents/base_agent.py`: Afegida funció `_call_claude_cli()` i detecció dual-mode
- `CLAUDE.md`: Documentació del model dual actualitzada

**Tests:**
- ✅ Test de traducció curta amb subscripció (cost €0.00)
- ✅ Parsing correcte de resposta JSON del CLI
- ✅ Detecció automàtica de context (CLAUDECODE=1)

**Resultat:**
- Mode subscripció funcional i testat
- Cost €0 per traduccions en Claude Code
- API reservada només per usuaris web que paguen
