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

### 🚨 REGLA OBLIGATÒRIA PER SCRIPTS DE TRADUCCIÓ

**TOTS els scripts que cridin agents de traducció HAN d'establir `CLAUDECODE=1` al principi del fitxer, ABANS d'importar els agents.**

```python
#!/usr/bin/env python3
"""Descripció de l'script..."""

import os
import sys

# ═══════════════════════════════════════════════════════════════════════════════
# OBLIGATORI: Establir CLAUDECODE=1 per usar subscripció (cost €0)
# Això ha d'anar ABANS d'importar els agents
# ═══════════════════════════════════════════════════════════════════════════════
os.environ["CLAUDECODE"] = "1"

# Ara ja es poden importar els agents
from agents.v2 import PipelineV2
# ...
```

**Per què és important:**
- Sense `CLAUDECODE=1`, els agents usen l'API i consumeixen crèdits ($$$)
- Amb `CLAUDECODE=1`, els agents usen el CLI amb subscripció (cost €0)
- **Mai oblidar aquesta línia en scripts nous de traducció!**

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

**Agents V2 (traducció):**
- `AnalitzadorPreTraduccio` - Anàlisi del text abans de traduir
- `TraductorEnriquit` - Traducció amb context ric
- `AvaluadorDimensional` - Avaluació en 3 dimensions (fidelitat, veu, fluïdesa)
- `RefinadorIteratiu` - Millora iterativa fins aprovació

**Agents auxiliars:**
- `GlossaristaAgent` - Crear glossaris terminològics
- `ChunkerAgent` - Dividir textos llargs en fragments
- `AnotadorCriticAgent` - Notes erudites
- `CercadorFontsAgent` - Cercar textos de domini públic
- `AgentRetratista` - Generar retrats d'autors
- `AgentPortadista` - Generar portades d'obres
- `WebPublisher` - Publicar la biblioteca web

**Pipeline V2:** `agents/v2/pipeline_v2.py` - Orquestració completa

**Dashboard de monitorització:** `dashboard/`
- S'obre automàticament al navegador quan comença una traducció
- Mostra progrés en temps real, logs, mètriques i gràfiques
- Ús: `from dashboard import start_dashboard, dashboard`

## Sistema de Portades (IMPORTANT)

**Cada obra NECESSITA una portada.** El build genera placeholders automàticament, però són temporals.

### Fitxers de portada
- Nom: `portada.png` (o `.jpg`)
- Ubicació: directori de l'obra (`obres/autor/obra/portada.png`)
- Format: PNG/JPG, proporció 2:3 (ex: 400x600px)

### Generar portades
```bash
# Veure obres sense portada real
python scripts/generar_portades.py --list

# Generar portades amb IA (requereix Venice.ai)
python scripts/generar_portades.py

# Regenerar totes
python scripts/generar_portades.py --all
```

### Build i portades
El `build.py` fa:
1. Copia `portada.png` de cada obra a `docs/assets/portades/{autor}-{obra}-portada.png`
2. Si no existeix portada, **genera un placeholder automàtic**
3. Mai desapareixeran portades - sempre hi haurà almenys un placeholder

### Agent Portadista
- Ubicació: `agents/portadista.py`
- Genera portades minimalistes amb Venice.ai
- Paletes per gènere: FIL, POE, TEA, NOV, SAG, ORI, EPO

## Estructura traduccions
```
obres/[categoria]/[autor]/[obra]/
├── fragments/        # Per col·laboració GitHub
├── discussions/      # Discussions crítiques
├── metadata.yml      # Metadades de l'obra
├── original.md       # Text original
├── traduccio.md      # Traducció amb marques [^N] per notes i [T] per glossari
├── notes.md          # Notes erudites (format ## [N] Títol)
├── glossari.yml      # Termes amb definicions
└── portada.png       # Portada de l'obra
```

## Sistema de Notes i Glossari

### Notes (`notes.md`)
- Format: `## [N] Títol de la nota` seguit del contingut
- Referències al text: `[^1]`, `[^2]`, etc. a `traduccio.md`
- El build converteix `[^N]` a hipervincles `<sup><a href="#nota-N">[N]</a></sup>`

### Glossari (`glossari.yml`)
- Format YAML amb camps: `id`, `grec`, `transliteracio`, `traduccio`, `definicio`
- Referències al text: `terme[T]` a `traduccio.md`
- El build converteix `terme[T]` a `<a href="#term-id" class="term">terme</a>`

### Tipus de notes
[T] Traducció | [L] Literària | [F] Filosòfica | [H] Històrica | [R] Referència | [C] Cultural | [B] Biogràfica

## Fitxa d'Obra (UI Web)

### Capçalera
- Portada, títol, autor, traductor, llengua original, any

### Detalls de traducció (col·lapsable)
- Estat, qualitat, capítols, paraules, data revisió, font original, contribuïdors

### Contingut bilingüe
- Vista: Original | Bilingüe | Traducció
- Índex de capítols amb navegació
- Paginació per capítols (← →)

### Notes i Glossari (col·lapsables)
- Clicar nota/terme → obre secció → scroll → ressaltat
- "↩ Tornar al text" → col·lapsa → torna a posició de lectura

### Altres funcionalitats
- Botó "Tornar a dalt" (apareix després de 300px scroll)
- Sistema de favorits
- Mode fosc compatible

## Criteris per gènere
- Filosofia: precisió terminològica
- Novel·la: veu narrativa
- Poesia: sentit + ritme
- Teatre: oralitat

## Documentació completa
Consulta `INSTRUCCIONS_CLAUDE_CODE.md` per documentació detallada dels agents i el pipeline.

## Contribucions
Totes les contribucions són benvingudes! Consulta CONTRIBUTING.md per més informació.
