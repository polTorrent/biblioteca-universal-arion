# 🌐 Configuració de la Web - Editorial Clàssica

Guia completa per utilitzar el sistema web de publicació de traduccions.

## 📋 Estructura Creada

Tots els components necessaris han estat creats:

```
editorial-classica/
├── FORMAT.md                         ✅ Especificació del format
├── agents/
│   └── formatter.py                  ✅ Agent de formatatge
├── web/
│   ├── css/
│   │   └── styles.css                ✅ CSS responsive (~830 línies)
│   ├── js/
│   │   └── app.js                    ✅ JavaScript amb classe EditorialClassica
│   └── templates/
│       ├── index.html                ✅ Template índex
│       └── obra.html                 ✅ Template per obres
├── scripts/
│   └── build.py                      ✅ Script de construcció
├── obres/
│   └── plato-banquet-exemple.md      ✅ Exemple d'obra
└── docs/                             ✅ Directori per HTML generat
```

## 🚀 Ús Bàsic

### 1. Crear una Obra Nova

Crea un fitxer `.md` a `obres/` seguint el format de `FORMAT.md`:

```bash
# Copia l'exemple
cp obres/plato-banquet-exemple.md obres/la-teva-obra.md

# Edita'l
nano obres/la-teva-obra.md
```

**Mínim requerit**: metadades YAML + contingut Markdown

### 2. Construir el HTML

```bash
# Construir totes les obres
python scripts/build.py

# Construir una obra específica
python scripts/build.py obres/la-teva-obra.md

# Netejar i reconstruir tot
python scripts/build.py --clean
```

### 3. Veure el Resultat

Obre `docs/index.html` en un navegador:

```bash
# Linux/Mac
open docs/index.html

# O amb un servidor local
cd docs
python -m http.server 8000
# Visita http://localhost:8000
```

## 📝 Format de les Obres

### Estructura Bàsica

```markdown
---
title: "Títol de l'obra"
author: "Autor"
translator: "Editorial Clàssica"
source_language: "grec"
date: "2026-01-25"
status: "revisat"
quality_score: 8.5
tags: ["filosofia", "diàleg"]
---

# Títol de l'obra

Contingut...
```

### Camps de Metadades

| Camp | Obligatori | Descripció |
|------|-----------|------------|
| `title` | ✅ | Títol en català |
| `author` | ✅ | Autor en català |
| `translator` | ✅ | Nom del traductor |
| `source_language` | ✅ | `grec` o `llatí` |
| `date` | ✅ | Data YYYY-MM-DD |
| `status` | ✅ | `esborrany`, `revisat`, `publicat` |
| `original_author` | ❌ | Nom original (grec/llatí) |
| `period` | ❌ | Període històric |
| `quality_score` | ❌ | Puntuació 1-10 |
| `tags` | ❌ | Etiquetes temàtiques |

### Elements Especials

#### Diàlegs

```markdown
**SÒCRATES** — Text del parlament.

**FEDRE** — Resposta.
```

#### Notes del Traductor

```markdown
El terme *daimon* [N.T.: esperit diví intermediari] és important.
```

#### Poesia

```markdown
    Oh déus immortals que habiteu l'Olimp,
    escolteu la nostra pregària sincera.
```

#### Glossari

```markdown
## Glossari

**Aretē** (ἀρετή)
Excel·lència, virtut. Concepte central de l'ètica grega.
```

## 🎨 Personalització

### CSS

Edita `web/css/styles.css` per canviar l'aparença:

```css
:root {
    --color-primary: #8B4513;     /* Color principal */
    --font-serif: 'Crimson Text', serif;  /* Font principal */
}
```

### JavaScript

Edita `web/js/app.js` per afegir funcionalitats:

```javascript
// La classe EditorialClassica ja té:
// - Dark mode
// - Cerca
// - TOC automàtica
// - Smooth scroll
// - Etc.
```

### Templates

Edita els fitxers a `web/templates/`:

- `index.html` - Pàgina principal
- `obra.html` - Plantilla per obres individuals

## 🔧 Integració amb el Pipeline

### Utilitzar FormatterAgent

```python
from agents import FormatterAgent, FormattingRequest, WorkMetadata, Section

# Crear agent
formatter = FormatterAgent()

# Preparar dades
metadata = WorkMetadata(
    title="El Banquet",
    author="Plató",
    source_language="grec",
    status="revisat",
    quality_score=8.5,
)

sections = [
    Section(
        title="Introducció",
        level=2,
        content="Text de la introducció...",
    )
]

# Formatar
request = FormattingRequest(
    metadata=metadata,
    sections=sections,
    output_path=Path("obres/banquet.md"),
)

markdown = formatter.format_work(request)
```

### Des del Pipeline de Traducció

Afegeix FormatterAgent al final del pipeline:

```python
from pipeline.translation_pipeline import TranslationPipeline
from agents import FormatterAgent

# ... després de traduir ...

# Formatar resultat
formatter = FormatterAgent()
# (implementar integració)
```

## 📊 Workflow Complet

```
1. TRADUIR
   pipeline.run() → PipelineResult

2. FORMATAR
   FormatterAgent → fitxer .md a obres/

3. CONSTRUIR
   scripts/build.py → HTML a docs/

4. PUBLICAR
   Pujar docs/ al servidor web
```

## 🌍 Publicació

### GitHub Pages

1. Puja el projecte a GitHub
2. Configura GitHub Pages per servir des de `/docs`
3. Visita `https://username.github.io/editorial-classica`

### Servidor Propi

```bash
# Copia docs/ al servidor
scp -r docs/* user@server:/var/www/html/

# O usa rsync
rsync -avz docs/ user@server:/var/www/html/
```

### Netlify / Vercel

1. Connecta el repositori
2. Configura:
   - Build command: `python scripts/build.py`
   - Publish directory: `docs`

## 🧪 Testing

### Test del Sistema Complet

```bash
# 1. Construir
python scripts/build.py

# 2. Verificar
ls -la docs/
# Hauries de veure:
# - index.html
# - plato-banquet-exemple.html
# - css/styles.css
# - js/app.js

# 3. Provar al navegador
python -m http.server 8000 -d docs
# Visita http://localhost:8000
```

### Validar Markdown

```python
from agents import FormatterAgent

formatter = FormatterAgent()
content = Path("obres/obra.md").read_text()

issues = formatter.validate_markdown(content)
if issues:
    for issue in issues:
        print(issue)
else:
    print("✅ Markdown vàlid")
```

## 📚 Exemples d'Ús

### Exemple 1: Obra Simple

```markdown
---
title: "Ètica a Nicòmac I"
author: "Aristòtil"
translator: "Editorial Clàssica"
source_language: "grec"
date: "2026-01-25"
status: "esborrany"
---

# Ètica a Nicòmac - Llibre I

## La felicitat com a bé suprem

Tota art i tota investigació...
```

### Exemple 2: Diàleg Complex

Veure `obres/plato-banquet-exemple.md` per un exemple complet amb:
- Metadades completes
- Diàlegs
- Notes del traductor
- Glossari
- Bibliografia

## 🐛 Troubleshooting

### Error: "Template no trobat"

```bash
# Verifica que existeix
ls web/templates/

# Si no, revisa la ruta al build.py
```

### El CSS no es carrega

```bash
# Verifica que s'ha copiat
ls docs/css/styles.css

# Reconstrueix
python scripts/build.py --clean
```

### Les metadades no es processen

```bash
# Verifica format YAML
# Ha de començar amb ---
# i acabar amb ---
```

## 🚀 Següents Passos

1. **Crea més obres** a `obres/`
2. **Personalitza l'estil** editant `web/css/styles.css`
3. **Afegeix funcionalitats** a `web/js/app.js`
4. **Integra amb el pipeline** de traducció
5. **Publica** a GitHub Pages o el teu servidor

## 📖 Documentació de Referència

- [FORMAT.md](FORMAT.md) - Especificació completa del format
- [README_PIPELINE.md](README_PIPELINE.md) - Pipeline de traducció
- [INTEGRACIO_AGENTS.md](INTEGRACIO_AGENTS.md) - Agents integrats

## 💡 Consells

### Bones Pràctiques

1. **Noms de fitxer**: Usa format `autor-obra.md` (e.g., `plato-republica.md`)
2. **Metadades**: Omple totes les opcionals per millor SEO
3. **Tags**: Usa tags coherents entre obres
4. **Qualitat**: Revisa abans de marcar com `publicat`

### Performance

- Les imatges haurien d'estar a `docs/images/`
- Usa lazy loading per imatges (`data-src`)
- El CSS i JS estan optimitzats per ser eficients

### SEO

- Omple sempre `description` a les metadades
- Usa `tags` rellevants
- Els templates ja tenen Open Graph i JSON-LD

---

**Tot llest per publicar!** 🎉

Si tens dubtes, consulta els exemples o revisa la documentació completa.
