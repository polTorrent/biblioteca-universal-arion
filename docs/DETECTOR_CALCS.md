# Detector de Calcs Lingüístics

## Visió General

El detector de calcs identifica construccions no naturals en català que provenen de traduccions literals d'altres llengües. S'integra amb l'avaluador de fluïdesa per millorar automàticament la qualitat de les traduccions.

## Llengües Suportades

| Llengua | Codi | Patrons Específics |
|---------|------|-------------------|
| Llatí | la, llatí, latin | Ablatius absoluts, genitiu partitiu |
| Grec | grc, grec, greek | μέν...δέ, partícules |
| Alemany | de, alemany, german | Verbs al final, compostos llargs |
| Anglès | en, anglès, english | Gerundis, passives |
| **Rus** | ru, rus, russian | Articles absents, doble negació |
| **Japonès** | ja, japonès, japanese | Ordre SOV, partícula wa, onomatopeies |
| **Àrab** | ar, àrab, arabic | Falta còpula, ordre VSO |
| **Xinès** | zh, xinès, chinese | Classificadors, tema-comentari |
| **Italià** | it, italià, italian | Falsos amics, "a" personal |
| **Portuguès** | pt, portuguès, portuguese | Falsos amics, gerundis |

## Tipus de Calcs Detectats

```python
class TipusCalc(str, Enum):
    HIPERBATON = "hiperbaton"           # Ordre de paraules no natural
    ABLATIU_ABSOLUT = "ablatiu_absolut" # "Dit això, marxà"
    PARTICIPI_PESAT = "participi_pesat" # Construccions participials
    PASSIVA_EXCESSIVA = "passiva_excessiva"
    GERUNDI_ANGLES = "gerundi_angles"   # "Estava sent fet"
    FALS_AMIC = "fals_amic"
    CALC_SINTACTIC = "calc_sintactic"
    ARTICLE_ABSENT = "article_absent"   # Del rus, àrab
    ARTICLE_SOBRER = "article_sobrer"
    VERB_FINAL = "verb_final"           # Del japonès, alemany
    COMPOST_EXCESSIU = "compost_excessiu"
    NEGACIO_DOBLE = "negacio_doble"
    PRONOM_REDUNDANT = "pronom_redundant"
    CONNECTOR_LLATI = "connector_llati"
```

## Ús

### Bàsic

```python
from utils.detector_calcs import detectar_calcs

resultat = detectar_calcs(
    text="Dit això, el rei marxà. Certament era noble.",
    llengua_origen="llatí"
)

print(f"Fluïdesa: {resultat.puntuacio_fluidesa}/10")
print(f"Calcs detectats: {resultat.num_calcs}")

for calc in resultat.calcs:
    print(f"  [{calc.tipus.value}] '{calc.text_original}'")
    print(f"    → {calc.suggeriment}")
```

### Amb Classe

```python
from utils.detector_calcs import DetectorCalcs

detector = DetectorCalcs(llengua_origen="japonès")
resultat = detector.detectar("Quant a ell, sempre tard arribar.")
```

## Patrons per Llengua

### Rus

| Patró | Problema | Exemple | Suggeriment |
|-------|----------|---------|-------------|
| Nom sense article | El rus no té articles | "Home va al mercat" | "L'home va al mercat" |
| Doble negació | никто не = ningú no | "Ningú no ho sap" | Revisar si és natural |
| Diminutius excessius | -чка, -ик freqüents | "caseta petitona" | Reduir diminutius |

```python
# Exemples detectats
"Home va al mercat"  # → article_absent
"Ningú no ho sap"    # → negacio_doble
```

### Japonès

| Patró | Problema | Exemple | Suggeriment |
|-------|----------|---------|-------------|
| Verb al final | Ordre SOV | "Ell el llibre llegir" | Reorganitzar a SVO |
| Topicalització | Partícula は (wa) | "Quant a ell, ..." | Eliminar si innecessari |
| Onomatopeies | ドキドキ no adaptat | "doki-doki" | Adaptar o descriure |
| Passiva perjudici | 迷惑の受身 | "Em van ser robats" | Veu activa |

```python
# Exemples detectats
"Quant a ell, sempre estudia"  # → calc_sintactic (wa)
"El menjar em va ser robat"    # → passiva_excessiva
```

### Àrab

| Patró | Problema | Exemple | Suggeriment |
|-------|----------|---------|-------------|
| Falta còpula | No hi ha "ser" al present | "El llibre bo" | "El llibre és bo" |
| Ordre VSO | Verb-Subjecte-Objecte | "Va dir el rei" | "El rei va dir" |
| Cadena genitius | Estat constructe | "la casa de l'home de..." | Simplificar |

```python
# Exemples detectats
"El llibre molt bo"      # → calc_sintactic (falta còpula)
"Va dir el rei la veritat"  # → calc_sintactic (VSO)
```

### Xinès

| Patró | Problema | Exemple | Suggeriment |
|-------|----------|---------|-------------|
| Classificadors | 一头牛 = un cap de bou | "Un cap de bou" | Adaptar |
| Tema-comentari | 这件事，我... | "Aquesta cosa, jo..." | Reformular |
| Repetició èmfasi | 很很大 | "molt molt gran" | Usar superlatius |

```python
# Exemples detectats
"Un cap de bou"    # → calc_sintactic (classificador)
"molt molt gran"   # → calc_sintactic (repetició)
```

### Llengües Romàniques (Italià, Portuguès)

| Patró | Problema | Exemple | Suggeriment |
|-------|----------|---------|-------------|
| "A" personal | Italià: Vedo a Maria | "Veig a la Maria" | Eliminar "a" |
| Gerundi continu | Sto mangiando | "Estic menjant" | Present simple |

## Falsos Amics

El detector inclou diccionaris de falsos amics per llengua:

```python
FALSOS_AMICS = {
    "italià": {
        "burro": ("burro", "mantega (no ase)"),
        "camera": ("camera", "habitació (no càmera)"),
        "salir": ("salire", "pujar (no sortir)"),
    },
    "portuguès": {
        "polvo": ("polvo", "pop/polp (no pols)"),
        "exquisit": ("esquisito", "estrany (no delicat)"),
    },
    "rus": {
        "magazín": ("магазин", "botiga (no revista)"),
    },
    # ... més llengües
}
```

## Integració amb Avaluador

El detector s'integra automàticament amb `AvaluadorFluidesa`:

```
┌──────────────────────────────────────┐
│         AvaluadorFluidesa            │
├──────────────────────────────────────┤
│  1. Detecció automàtica (regex)      │ ← DetectorCalcs
│  2. Avaluació LLM (informat)         │
│  3. Puntuació combinada              │
│     70% LLM + 30% detector           │
└──────────────────────────────────────┘
```

## Extensió

Per afegir una nova llengua:

1. Afegir variants de nom a `_detectar_per_llengua()`:
```python
elif llengua in ["nova", "new", "nv"]:
    calcs.extend(self._detectar_calcs_nova(text))
```

2. Crear mètode de detecció:
```python
def _detectar_calcs_nova(self, text: str) -> list[CalcDetectat]:
    calcs = []
    # Patrons específics...
    return calcs
```

3. Afegir falsos amics:
```python
FALSOS_AMICS["nova"] = {
    "paraula": ("original", "significat real"),
}
```

## Severitat

| Tipus | Severitat | Descripció |
|-------|-----------|------------|
| GERUNDI_ANGLES | 8.0 | Molt evident |
| PASSIVA_EXCESSIVA | 7.0 | Clarament no natural |
| HIPERBATON | 6.0 | Ordre estrany |
| FALS_AMIC | 6.0 | Error semàntic |
| ARTICLE_ABSENT | 5.0 | Falta element |
| VERB_FINAL | 5.0 | Estructura alterada |
| CALC_SINTACTIC | 4.0 | Estructura copiada |
| NEGACIO_DOBLE | 3.0 | Pot ser correcte |
| CONNECTOR_LLATI | 3.0 | Només formal |

## Puntuació

```
Puntuació = 10 - (Σ severitat × 0.1) × factor_longitud

factor_longitud = min(1.0, paraules / 100)
```

- 10.0: Text perfectament natural
- 7-9: Petites rigideses
- 5-7: Es nota que és traducció
- <5: Clarament "traduït"

---

*Documentació generada: 2026-01-30*
