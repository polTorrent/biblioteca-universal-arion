# Biblioteca Universal Arion - Context per Claude Code

## ⚠️ AUTENTICACIÓ - MODEL DUAL

### 🤖 Claude Code (desenvolupament intern)
**SEMPRE usa subscripció Claude Pro/Max, MAI crèdits API.**

- Verificar abans de res: `claude auth status`
- Ha de dir "Authenticated via Claude subscription"
- Si demana API key → NO introduir-la → usar `claude auth login`
- **Motiu:** Cost fix mensual ($20-200) vs pay-per-token

### 🌐 Usuaris web (mode on-demand)
**Usen crèdits API només quan paguen per traduccions.**

- API d'Anthropic activada amb `use_api=True` en AgentConfig
- Cost cobrat a l'usuari per traducció (pay-per-token)
- **Motiu:** Model de negoci sostenible per usuaris externs

### 📊 Detecció automàtica
Els agents detecten automàticament el context:
- `CLAUDECODE=1` → Subscripció (cost fix)
- Context web → API (usuari paga)

### ✅ ESTAT ACTUAL
**Implementació completa!** Els agents detecten automàticament el context i utilitzen:
- 🤖 **Claude CLI** quan CLAUDECODE=1 (subscripció, cost €0)
- 🌐 **Anthropic API** en context web (usuaris paguen)

**Testat i validat:**
- ✅ Mode subscripció funcional amb cost €0
- ✅ Parsing correcte de resposta JSON del CLI
- ✅ Fallback a API quan es requereix

## Projecte
Biblioteca oberta i col·laborativa de traduccions al català d'obres clàssiques universals.

## Idioma de treball
Català sempre per documentació, codi i comunicació.

## Model col·laboratiu
- Traduccions inicials generades per IA
- Perfeccionament via GitHub (correccions, notes, discussions)
- Actualització mensual de la web
- Comunitat coordinada via Discord

## Pipeline de Traducció

```
0. VERIFICAR AUTENTICACIÓ (subscripció, no API!)
   ↓
1. glossari → 2. traducció → 3. perfeccionament → 4. anotació → 5. format web
```

**Agents principals:**
- `PerfeccionamentAgent` - Fusió holística (naturalització + correcció + estil)
- `AnotadorCriticAgent` - Notes erudites opcionals
- `Checkpointer` - Persistència per recuperar pipelines interromputs

**Agents deprecats:** `CorrectorAgent`, `EstilAgent` (usar `PerfeccionamentAgent`)

## Estructura traduccions
```
obres/[categoria]/[autor]/[obra]/
├── fragments/        # Per col·laboració GitHub
├── discussions/      # Discussions crítiques
├── metadata.yml
├── original.md
├── traduccio.md
└── glossari.yml
```

## Notes
[T] Traducció | [L] Literària | [F] Filosòfica | [H] Històrica | [R] Referència | [C] Cultural | [B] Biogràfica

## Criteris per gènere
- Filosofia: precisió terminològica
- Novel·la: veu narrativa
- Poesia: sentit + ritme
- Teatre: oralitat

## Documentació completa
Consulta `INSTRUCCIONS_CLAUDE_CODE.md` per documentació detallada dels agents i el pipeline.

## Contribucions
Totes les contribucions són benvingudes! Consulta CONTRIBUTING.md per més informació.
