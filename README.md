<p align="center">
  <strong>Biblioteca Universal Arion</strong><br>
  <em>Clàssics universals, en català, creats per tothom</em>
</p>

<p align="center">
  <a href="https://poltorrent.github.io/editorial-classica/"><img alt="Web" src="https://img.shields.io/badge/web-GitHub_Pages-blue?style=flat-square"></a>
  <a href="LICENSE"><img alt="Codi: MIT" src="https://img.shields.io/badge/codi-MIT-green?style=flat-square"></a>
  <a href="https://creativecommons.org/licenses/by-sa/4.0/"><img alt="Traduccions: CC BY-SA 4.0" src="https://img.shields.io/badge/traduccions-CC_BY--SA_4.0-orange?style=flat-square"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white">
  <img alt="Obres" src="https://img.shields.io/badge/obres-~100-purple?style=flat-square">
  <img alt="Autors" src="https://img.shields.io/badge/autors-86-purple?style=flat-square">
  <img alt="Llengües" src="https://img.shields.io/badge/lleng%C3%BCes_origen-12+-red?style=flat-square">
</p>

---

Biblioteca oberta de traduccions al **català** d'obres clàssiques universals — filosofia, narrativa, poesia, teatre, assaig i textos orientals. Edició crítica bilingüe amb glossari, notes i context acadèmic.

## Catàleg

**107 obres** de **86 autors**, des del sànscrit antic fins al segle XX, organitzades en 6 categories:

| Categoria | Obres | Autors destacats |
|-----------|:-----:|------------------|
| **Filosofia** | 23 | Plató, Aristòtil, Epictet, Sèneca, Marc Aureli, Heràclit, Spinoza, Nietzsche |
| **Narrativa** | 27 | Kafka, Txèkhov, Poe, Dostoievski, Boccaccio, Apuleu, Pu Songling |
| **Poesia** | 22 | Shakespeare, Safo, Baudelaire, Petrarca, Dante, Leopardi, Rilke, Li Bai |
| **Teatre** | 14 | Sòfocles, Eurípides, Aristòfanes, Èsquil, Ibsen, Strindberg, Zeami |
| **Oriental** | 12 | Laozi, Confuci, Zhuangzi, Matsuo Bashō, Kamo no Chōmei, Vyasa |
| **Assaig** | 9 | Ciceró, Montaigne, Plutarc, Sei Shōnagon, Pseudo-Longí |

**Llengües d'origen**: grec antic, llatí, anglès, alemany, francès, italià, rus, xinès clàssic, japonès clàssic, persa, sànscrit, hebreu antic i més.

### Obres destacades

| Obra | Autor | Llengua | Qualitat |
|------|-------|---------|:--------:|
| Meditacions | Marc Aureli | Llatí | 8.0 |
| Fragments | Heràclit | Grec | 8.6 |
| El retrat oval | E. A. Poe | Anglès | 8.5 |
| El llibre del coixí | Sei Shōnagon | Japonès | 8.0 |
| Capítols interiors | Zhuangzi | Xinès | 8.0 |
| Sonets (selecció) | Shakespeare | Anglès | 8.0 |
| Tao Te King | Laozi | Xinès | 8.0 |
| Laelius de Amicitia | Ciceró | Llatí | 7.5 |
| Shahnameh: Rostam i Sohrab | Firdawsí | Persa | 7.5 |
| Fragments (30 poemes) | Safo | Grec | 7.5 |

> Qualitat avaluada en 3 dimensions: fidelitat al text, veu de l'autor i fluïdesa en català.

## Com funciona

El projecte combina traducció assistida per IA amb revisió humana col·laborativa.

### Pipeline de traducció

```
Investigador → Glossarista → Chunker → [ Anàlisi → Traducció → Avaluació → Refinament ] → Fusió → Validació
```

Una cadena d'agents especialitzats processa cada obra:

- **Investigació**: context històric, cultural i filològic de l'autor i l'obra
- **Glossari**: terminologia clau amb transliteració i equivalències
- **Traducció enriquida**: amb context, few-shot i memòria entre fragments
- **Avaluació dimensional**: fidelitat (25%) + veu de l'autor (40%) + fluïdesa (35%)
- **Refinament iteratiu**: correcció automàtica segons el feedback de l'avaluador
- **Detecció de calcs**: identificació de construccions no naturals en català

### Sistema autònom

Un heartbeat cada 2 hores genera tasques de traducció, revisió i correcció. Un worker les processa en loop continu amb retry, rate-limit handling i validació post-execució.

```bash
# Gestió de tasques
bash scripts/task-manager.sh list
bash scripts/task-manager.sh status

# Worker
bash scripts/claude-worker-mini.sh
```

## Estructura d'una obra

```
obres/<categoria>/<autor>/<obra>/
├── metadata.yml          # Metadades: autor, llengua, estat, qualitat
├── original.md           # Text original (domini públic)
├── traduccio.md          # Traducció al català
├── glossari.yml          # Termes clau amb transliteració
├── notes.md              # Notes del traductor
├── introduccio.md        # Introducció crítica
├── portada.png           # Portada generada
└── fragments/            # Fragments editables per col·laboració
```

## Instal·lació

```bash
git clone https://github.com/poltorrent/editorial-classica.git
cd editorial-classica
pip install -e ".[dev]"
```

### Dependències principals

`anthropic` `pydantic` `rich` `tenacity` `httpx` `jinja2` `pyyaml` `markdown`

### Build de la web

```bash
python3 scripts/build.py          # Genera HTML a docs/
python3 scripts/build.py --clean  # Rebuild complet
```

### Tests

```bash
python3 -m pytest tests/ -v
ruff check agents/ utils/ core/ scripts/
```

## Com contribuir

Totes les traduccions es poden millorar. Pots:

- Corregir errors ortogràfics, gramaticals o de normativa
- Proposar millores de traducció o interpretació
- Afegir notes crítiques o context acadèmic
- Obrir discussions sobre passatges concrets
- Completar traduccions inacabades

Consulta [CONTRIBUTING.md](community/CONTRIBUTING.md) per més detalls.

## Llicències

| Component | Llicència |
|-----------|-----------|
| Traduccions | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| Codi | [MIT](LICENSE) |
| Textos originals | Domini públic |

## Enllaços

- [Web del projecte](https://poltorrent.github.io/editorial-classica/)
- [Guia de contribució](community/CONTRIBUTING.md)

---

<p align="center"><strong>Biblioteca Universal Arion</strong> &copy; 2026</p>
