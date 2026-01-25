# Editorial Classica

**Traduccions obertes de textos classics grecollatins al catala**

[![License: CC BY-SA 4.0](https://img.shields.io/badge/License-CC%20BY--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-sa/4.0/)

---

## Que es?

Editorial Classica es un projecte obert per traduir textos classics
grecollatins al catala, combinant intelligencia artificial amb revisio
humana experta.

---

## Traduccions Disponibles

| Obra | Autor | Estat | Llengua |
|------|-------|-------|---------|
| Enchiridion (caps. 1-5) | Epictetus | Completa | Grec |
| *Mes properament...* | | | |

---

## Caracteristiques

- **Bilingue** - Text original i traduccio en parallel
- **Notes hiperlinkades** - Context i explicacions accessibles
- **Glossari interactiu** - Termes tecnics explicats
- **Disseny elegant** - Tipografia i colors classics
- **Responsive** - Funciona en mobil i desktop
- **Obert** - Tot el contingut es lliure (CC BY-SA 4.0)

---

## Com Contribuir

Busquem collaboradors per:

- Revisar traduccions - Correccions i millores
- Proposar obres - Suggerir nous textos a traduir
- Reportar errors - Issues amb problemes detectats
- Millorar el codi - Frontend, pipeline, agents

Consulta [CONTRIBUTING.md](CONTRIBUTING.md) per mes detalls.

---

## Tecnologia

- **Pipeline de traduccio:** Python + Claude API (Anthropic)
- **Agents:** Chunker, Glossari, Traductor, Corrector, Formatter
- **Web:** HTML5 + CSS3 + JavaScript vanilla
- **Publicacio:** GitHub Pages

---

## Desenvolupament Local

```bash
# Clonar repositori
git clone https://github.com/USUARI/editorial-classica.git
cd editorial-classica

# Installar dependencies
pip install -r requirements.txt

# Generar web
python scripts/build.py

# Veure localment
cd docs && python -m http.server 8000
# Obre http://localhost:8000
```

---

## Llicencia

- **Traduccions:** [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)
- **Codi:** [MIT License](LICENSE)

---

## Credits

Projecte creat amb dedicacio per la difusio de la cultura classica en catala.

---

*Aei aristeuein - Sempre excellir*
