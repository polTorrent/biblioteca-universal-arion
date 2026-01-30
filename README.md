# 📚 Biblioteca Universal Arion

Biblioteca oberta i col·laborativa de traduccions al català d'obres clàssiques universals.

## 🎯 Missió

Traduir obres mestres de la literatura i filosofia universal al català, amb edició crítica bilingüe, de forma oberta i col·laborativa.

## 📖 Catàleg actual

| Autor | Obra | Idioma | Estat |
|-------|------|--------|-------|
| Epictetus | Enchiridion | Grec | ✅ Completat |
| Plató | Critó | Grec | 🔄 En procés |
| Sèneca | Epístola 1 | Llatí | 🔄 En procés |
| Schopenhauer | La quàdruple arrel | Alemany | 🔄 En procés |

## 🤝 Com contribuir

Totes les traduccions es poden millorar! Pots:

- 🔤 Corregir errors ortogràfics o gramaticals
- 📝 Proposar millores de traducció
- 💬 Obrir discussions sobre interpretacions
- 📚 Afegir notes crítiques o context

Consulta [CONTRIBUTING.md](community/CONTRIBUTING.md) per més detalls.

## 📁 Estructura del projecte
```
obres/[autor]/[obra]/
├── fragments/        # Fragments editables per col·laboració
├── discussions/      # Discussions crítiques
├── metadata.yml      # Metadades de l'obra
├── original.md       # Text original
├── traduccio.md      # Traducció consolidada
└── glossari.yml      # Glossari de termes
```

## 🛠️ Tecnologia

- **Traducció inicial**: Claude (Anthropic)
- **Col·laboració**: GitHub
- **Comunitat**: Discord
- **Web**: GitHub Pages

## 🚀 Pipeline de Traducció V2

El sistema utilitza una arquitectura d'agents especialitzats:

```
Investigador → Glossarista → Chunker → Traductor → Avaluador → Refinador → Validador
```

### Característiques principals

- **Investigació automàtica**: Context històric i cultural de l'autor i obra
- **Memòria contextual**: Coherència entre chunks de traducció
- **Avaluació dimensional**: Fidelitat + Veu de l'autor + Fluïdesa
- **Detector de calcs**: Identificació automàtica de construccions no naturals
- **Persistència**: Reprendre traduccions interrompudes
- **Dashboard**: Monitorització en temps real al navegador

### Ús bàsic

```python
import os
os.environ["CLAUDECODE"] = "1"  # Usar subscripció

from agents.v2 import PipelineV2, ConfiguracioPipelineV2

config = ConfiguracioPipelineV2(
    fer_investigacio=True,
    habilitar_persistencia=True,
)
pipeline = PipelineV2(config=config)

resultat = pipeline.traduir(
    text=text_original,
    llengua_origen="grec",
    autor="Plató",
    obra="Apologia de Sòcrates",
)
```

### Documentació tècnica

Consulta [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md) per documentació completa del sistema.

## 📜 Llicència

- **Traduccions**: CC BY-SA 4.0
- **Codi**: MIT
- **Originals**: Domini públic

## 🔗 Enllaços

- [Web](https://poltorrent.github.io/editorial-classica/)
- [Discord](#) *(properament)*

---

*"Clàssics universals, en català, creats per tothom"*

**Biblioteca Universal Arion © 2026**
