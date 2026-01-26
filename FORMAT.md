# Format de Traduccions Editorial Clàssica

Especificació del format Markdown per a traduccions de textos clàssics universals.

## Estructura General

```markdown
---
title: "Títol de l'obra"
author: "Autor (en català)"
original_author: "Autor original (grec/llatí)"
translator: "Traductor/a"
source_language: "grec" | "llatí"
date: "2026"
status: "esborrany" | "revisat" | "publicat"
quality_score: 7.5
tags: ["filosofia", "diàleg", "ètica"]
---

# Títol de l'obra

**Autor**: Nom de l'autor
**Traductor**: Nom del traductor
**Any**: 2026

## Pròleg

[Text del pròleg o introducció]

## Text Principal

[Contingut de la traducció]

## Notes del Traductor

[Notes i aclariments]

## Glossari

[Termes i definicions]

## Bibliografia

[Referències utilitzades]
```

## Metadades (YAML Front Matter)

Tots els fitxers de traduccions han de començar amb metadades en format YAML:

```yaml
---
title: "El Banquet"
author: "Plató"
original_author: "Πλάτων (Plátōn)"
original_title: "Συμπόσιον (Sympósion)"
translator: "Editorial Clàssica"
source_language: "grec"
period: "Període clàssic (385 aC)"
genre: "Diàleg filosòfic"
date: "2026-01-25"
status: "revisat"
quality_score: 8.5
revision_rounds: 2
total_cost_eur: 3.45
tags: ["filosofia", "diàleg", "amor", "bellesa", "ètica"]
---
```

### Camps Obligatoris

| Camp | Tipus | Descripció |
|------|-------|------------|
| `title` | String | Títol de l'obra en català |
| `author` | String | Nom de l'autor en català |
| `translator` | String | Traductor o entitat |
| `source_language` | Enum | `grec` o `llatí` |
| `date` | Date | Data de traducció (YYYY-MM-DD) |
| `status` | Enum | `esborrany`, `revisat`, `publicat` |

### Camps Opcionals

| Camp | Tipus | Descripció |
|------|-------|------------|
| `original_author` | String | Nom original en grec/llatí |
| `original_title` | String | Títol original |
| `period` | String | Període històric |
| `genre` | String | Gènere literari |
| `quality_score` | Float | Puntuació 1-10 |
| `revision_rounds` | Integer | Rondes de revisió |
| `total_cost_eur` | Float | Cost de producció |
| `tags` | Array | Etiquetes temàtiques |
| `isbn` | String | ISBN si està publicat |
| `editor` | String | Editor responsable |

## Estructura del Contingut

### 1. Capçalera Principal

```markdown
# El Banquet

**Autor**: Plató
**Traductor**: Editorial Clàssica
**Any**: 2026

> Diàleg filosòfic sobre la naturalesa de l'amor i la bellesa.
```

### 2. Seccionament

#### Obres amb capítols/llibres:

```markdown
## Llibre I

### Capítol 1: El pròleg d'Apol·lodor

[Text del capítol]

### Capítol 2: El convit d'Agató

[Text del capítol]
```

#### Diàlegs amb parlaments:

```markdown
## El discurs de Sòcrates

**SÒCRATES** — Doncs bé, amics meus, us diré el que vaig aprendre...

**AGATÓ** — I què vas aprendre, Sòcrates?

**SÒCRATES** — Que l'amor no és altra cosa que...
```

#### Poesia/tragèdia:

```markdown
## Acte I: Escena 1

**COR**
Oh déus immortals que habiteu l'Olimp,
escolteu la nostra pregària sincera.

**PROTAGONISTA**
Ciutadans d'Atenes, avui us parlo
amb el cor oprimit pel dolor.
```

### 3. Notes del Traductor

Les notes es poden integrar de dues maneres:

#### Notes a peu (inline):

```markdown
Sòcrates parla del *daimon* [N.T.: esperit o geni personal] que el guia.
```

#### Notes al final de secció:

```markdown
## Notes del Traductor

1. **Daimon**: En grec δαίμων, refereix a un esperit o divinitat menor que actua com a guia personal. No té les connotacions negatives del terme "dimoni" modern.

2. **Simposion**: El banquet grec era una institució social on es combinava menjar, beure vi i conversa filosòfica.
```

### 4. Glossari

```markdown
## Glossari

**Aretē** (ἀρετή)
Excel·lència, virtut. Concepte central de l'ètica grega que designa la realització plena del potencial d'una persona o cosa.

**Eudaimonia** (εὐδαιμονία)
Felicitat, vida plena. No és un estat emocional temporal, sinó la realització completa de la vida humana.

**Logos** (λόγος)
Raó, paraula, discurs. Terme polisèmic que pot significar des de la capacitat racional fins al principi ordenador de l'univers.
```

### 5. Referències i Bibliografia

```markdown
## Bibliografia

### Edicions crítiques consultades

- **OCT** (Oxford Classical Texts): Burnet, J. (1903). *Platonis Opera*, vol. II. Oxford: Clarendon Press.
- **Budé**: Robin, L. (1929). *Platon: Le Banquet*. Paris: Les Belles Lettres.

### Traduccions de referència

- Lledó, E. (1988). *Diàlogos III: El Banquete*. Madrid: Gredos.
- Rowe, C. J. (1998). *Plato: Symposium*. Warminster: Aris & Phillips.

### Estudis

- Dover, K. J. (1980). *Plato: Symposium*. Cambridge: Cambridge University Press.
- Nussbaum, M. (2001). *The Fragility of Goodness*. Cambridge: Cambridge UP.
```

## Convencions Tipogràfiques

### Èmfasi i Destacats

```markdown
*Cursiva* - per a termes estrangers i èmfasi lleu
**Negreta** - per a noms de parlants i èmfasi fort
***Negreta cursiva*** - per a títols d'obres citades
`Codi` - per a termes tècnics o transliteracions
```

### Citacions

```markdown
> Citació curta en bloc

> Citació més llarga que ocupa
> diverses línies i que manté
> el format de bloc.

>> Citació dins d'una citació
```

### Noms Propis

- **Noms de persona**: Forma catalana tradicional quan existeixi (Plató, Aristòtil, Ciceró), original transliterat si no (Alcibíades, Fedre).
- **Noms de lloc**: Forma catalana (Atenes, Roma, Esparta).
- **Divinitats**: Forma llatina tradicional (Zeus, Apol·lo, Afrodita).

### Transliteració

#### Del grec:

- Utilitzar transliteració estàndard: α→a, β→b, γ→g, δ→d, etc.
- Mantenir diacrítics quan sigui necessari: ē, ō per a vocals llargues
- Exemple: Σωκράτης → Sōkrátēs (en contextos acadèmics)

#### Del llatí:

- Respectar la grafia original
- Marcar vocals llargues si cal: ā, ē, ī, ō, ū
- Exemple: Cicerō, Vergilius

## Marcatge Semàntic

### Parlaments de diàleg

```markdown
**SÒCRATES** — Text del parlament.

**FEDRE** — Resposta.
```

### Fragments poètics

```markdown
    Oh musa, canta'm la ira d'Aquil·les,
    fill de Peleu, que portà tants mals als aqueus,
    i envià a l'Hades moltes ànimes valentes.
```

### Referències internes

```markdown
Com ja hem dit al [Capítol 2](#capítol-2), Sòcrates afirma...

Vegeu també la discussió sobre la virtut a [Menó §80d](#menó-80d).
```

### Referències externes

```markdown
Segons [Aristòtil, *Ètica a Nicòmac* I.7](bibliografia.md#aristotil-etica),
la felicitat és...
```

## Metadades de Seccions

Cada secció important pot tenir metadades opcionals:

```markdown
## El discurs d'Agató
<!-- section-meta
speaker: "Agató"
type: "discurs"
length: "mitjà"
themes: ["bellesa", "amor", "retòrica"]
original: "174a-178a"
-->

[Text del discurs]
```

## Formats Especials

### Taules comparatives

```markdown
| Grec | Transliteració | Català | Significat |
|------|----------------|--------|------------|
| ἀρετή | aretḗ | virtut | excel·lència |
| λόγος | lógos | raó | discurs, raó |
| ψυχή | psykhḗ | ànima | esperit, vida |
```

### Esquemes i diagrames

```markdown
## Estructura del diàleg

```
El Banquet
├── Pròleg (Apol·lodor)
├── Marc narratiu (Aristòdem)
└── Discursos sobre l'amor
    ├── Fedre
    ├── Pausànias
    ├── Erixímac
    ├── Aristòfanes
    ├── Agató
    ├── Sòcrates/Diòtima
    └── Alcibíades
```
```

### Cronologies

```markdown
## Context històric

- **430 aC** - Naixement de Plató
- **399 aC** - Mort de Sòcrates
- **387 aC** - Fundació de l'Acadèmia
- **385 aC** - Composició probable del *Banquet*
- **347 aC** - Mort de Plató
```

## Format de Sortida

Els fitxers Markdown seran convertits a HTML amb el script `scripts/build.py`:

```bash
python scripts/build.py obres/plato-banquet.md
```

Generarà:

```
docs/
└── plato-banquet/
    ├── index.html
    ├── capitol-1.html
    ├── capitol-2.html
    └── ...
```

## Validació

Un fitxer vàlid ha de:

1. ✅ Tenir metadades YAML completes
2. ✅ Començar amb capçalera de nivell 1 (`#`)
3. ✅ Tenir almenys un dels camps: `author`, `translator`
4. ✅ Utilitzar només capçaleres de nivell 1-4
5. ✅ Tenir extensions `.md` o `.markdown`
6. ✅ Estar codificat en UTF-8

## Exemple Complet

Vegeu:
- `obres/plato-banquet.md` - Exemple de diàleg
- `obres/vergilius-eneida-llibre-i.md` - Exemple de poesia
- `obres/cicero-primera-catilinaria.md` - Exemple d'oratòria

## Extensions Futures

- Suport per a aparell crític (variants textuals)
- Notes al marge amb marcatge `aside`
- Índex onomàstic automatitzat
- Enllaços al Perseus Digital Library

---

**Versió**: 1.0
**Data**: Gener 2026
**Editorial Clàssica**
