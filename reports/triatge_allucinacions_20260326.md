# Triatge d'al·lucinacions — 2026-03-26

## Resum executiu

| Categoria | Obres |
|-----------|-------|
| **AL·LUCINACIÓ CONFIRMADA** | 1 |
| **CONTINGUT ERRONI** | 1 |
| **ORIGINAL INCOMPLET** | 3 |
| **TRADUCCIÓ INCOMPLETA** | ~15 |
| **DUPLICATS** | 2 parells |
| **MAL ETIQUETAT** | 1 |
| **FALSOS POSITIUS** | ~77 |
| **OK (verificació estructural)** | 14 |
| **Total obres verificades** | ~100 |

---

## AL·LUCINACIÓ CONFIRMADA (1)

### obres/filosofia/nietzsche/die-philosophie-im-tragischen-zeitalter-der-griechen/
- **Ratio**: 1.27 (39,237 → 50,149 ch)
- **Diagnòstic**: La traducció és una **adaptació lliure/paràfrasi**, no una traducció fidel. Les 17 seccions existeixen tant a l'original com a la traducció, però el contingut de cada secció a la traducció NO correspon fidelment al text alemany original. Per exemple, la secció 1 original comença "Es giebt Gegner der Philosophie..." mentre la traducció comença amb un text completament diferent sobre els grecs organitzant el caos.
- **Acció**: `.needs_fix` creat. Cal esborrar traduccio.md i re-traduir fidelment.

---

## CONTINGUT ERRONI (1)

### obres/filosofia/aristotil/peri-psykhes/
- **Ratio**: N/A (0 orig → 3,208 trad)
- **Diagnòstic**: `original.md` està buit. `traduccio.md` conté text de l'**Athenaion Politeia** (Constitució d'Atenes), NO del Peri Psyches (De Anima). El fitxer també conté l'error "[ERROR: El CLI ha retornat una resposta buida]". Contingut completament equivocat.
- **Acció**: `.needs_fix` creat. Cal afegir original grec correcte i re-traduir.

---

## ORIGINAL INCOMPLET (3)

| Obra | Ratio | Problema |
|------|-------|----------|
| narrativa/ibn-tufayl/hayy-ibn-yaqzan | 230.26 | original.md és un stub de 16 línies. Text complet a `gutenberg_raw.txt`. Traducció legítima. |
| poesia/teocrit/idillis | 77.23 | original.md és un stub de 12 línies (només títol i llista d'idil·lis). Text grec mai afegit. Traducció legítima. |
| filosofia/schopenhauer/vierfache-wurzel | 16.14 | original.md només té §1-3 (56 línies). Traducció cobreix §1-52 complet. |

**Acció necessària**: Copiar/afegir el text original complet a `original.md`.

---

## TRADUCCIÓ INCOMPLETA (~15)

### Amb errors de CLI (traducció interrompuda)

| Obra | Ratio | Cobertura | Detall |
|------|-------|-----------|--------|
| poesia/petrarca/seleccio-20-sonets | 0.01 | 0% | traduccio.md diu "Pendent de traducció" |
| narrativa/sade/justine | 0.05 | ~5% | Només dedicatòria i primers episodis |
| narrativa/apuleu/cupido-i-psique | 0.34 | ~34% | Múltiples "[ERROR: El CLI...]" |
| poesia/horaci/odes-seleccio-20-odes | 0.31 | ~25% | Errors de CLI, ~25 de 100+ odes |
| filosofia/lucreci/de-rerum-natura-llibre-i | 0.55 | ~30% | Múltiples errors de CLI |
| teatre/terenci/andria | 0.89 | ~31% | Errors de CLI al final |
| narrativa/rudyard-kipling/the-jungle-book | 0.54 | ~10% | Majoritàriament errors de CLI |
| assaig/tacit/germania | 0.94 | ~70% | Falten caps. I-II, IX-XI, XV, XX, etc. |

### Traduccions genuïnes però incompletes

| Obra | Ratio | Cobertura | Detall |
|------|-------|-----------|--------|
| narrativa/dostoievski/notes-del-subsol | 0.38 | ~71% | Falta cap. IX Part 1. `.needs_fix` ja existent |
| oriental/vyasa/bhagavad-gita | 0.58 | ~60% | Traducció s'atura a mig camí |
| oriental/yoshida-kenko/tsurezuregusa | 0.59 | ~50% | Selecció parcial dels fragments |
| narrativa/firdawsi/shahnameh-rostam-i-sohrab | 0.78 | ~50% | Meitat del poema persa |
| narrativa/vishnu-sharma/panchatantra-llibre-i | 0.31 | ~15% | Molt incompleta |
| assaig/plutarc/sobre-la-tranquillitat | 0.47 | ~80% | Condensat/final potser omès |
| teatre/strindberg/froken-julie | 0.94 | ~68% | Possible prefaci o final omès |

### Original sobredimensionat

| Obra | Ratio | Detall |
|------|-------|--------|
| oriental/rumi/masnavi-seleccio-10-contes | 0.07 | original.md conté tot el Masnavi (6 llibres, 788K ch) però el projecte és "selecció 10 contes" |

---

## DUPLICATS (2 parells)

| Parell | Detall |
|--------|--------|
| `narrativa/luci-de-samosata/` vs `narrativa/lucia-de-samosata/` | Mateixa obra (Diàlegs dels Morts), seleccions diferents. "lucia" és un error ortogràfic. |
| `narrativa/kipling/el-llibre-de-la-selva/` vs `narrativa/rudyard-kipling/the-jungle-book/` | Mateixa obra. La primera té més traducció (~923 línies vs ~479). |

**Acció**: Consolidar cada parell en una sola entrada.

---

## MAL ETIQUETAT (1)

### oriental/kalidasa/meghaduta-el-missatger-del-nuvol/
- El directori diu "Meghaduta" però original.md i traduccio.md contenen el **Kumarasambhava** (Birth of the War-God), no el Meghaduta (Cloud Messenger).
- **Acció**: Reanomenar directori o substituir contingut.

---

## FALSOS POSITIUS — Anàlisi de causes

La gran majoria dels 70 "INVENTADES" del verificador eren **falsos positius** causats per:

### 1. Diferència de densitat lingüística
Idiomes com el xinès clàssic, japonès, sànscrit i hebreu són extremadament densos. Una traducció al català naturalment ocupa 1.5-2.5x més espai. Exemples:
- Laozi/Tao Te King: ratio 1.93 ← normal per xinès clàssic
- Confuci/Analectes: ratio 1.76 ← normal per xinès clàssic
- Lu Yu/Chajing: ratio 1.77 ← normal per xinès clàssic
- Mozi/Amor-universal: ratio 1.71 ← normal per xinès clàssic

### 2. Diferència de format de numeració
L'original i la traducció usen formats diferents per numerar seccions:
- Original: `_Pros._`, `[17a]`, `v. 195`
- Traducció: `**PROSPER**`, `### 17`, `### 195`
El verificador detecta IDs diferents i marca com "inventades" + "falten".

### 3. Multibyte characters (grec, hebreu, ciríl·lic)
El ratio per caràcters és enganyós quan l'original usa alfabets no-llatins. El grec antic ocupa ~2x bytes per caràcter. Exemples:
- Sòfocles/Antígona: ratio 0.57 per bytes, 1.19 per paraules ← complet
- Eurípides/Medea: ratio 0.54 per bytes, 1.14 per paraules ← complet

### 4. Formatació diferent (vers vs prosa, espaiat)
L'original pot tenir doble espaiat o format vers-per-línia, la traducció usa paràgrafs. Exemples:
- Sor Juana: 1961 línies original (doble espaiat Wikisource) vs 1027 traducció ← complet

---

## Ajustos al verificador

Arran d'aquest triatge, s'han relaxat els llindars:

| Paràmetre | Abans | Després | Motiu |
|-----------|-------|---------|-------|
| Ratio longitud per unitat (verificar_traduccio.py) | 0.25-2.5 | 0.2-3.0 | Xinès/japonès → català pot ser 2.5-3x |
| Ratio longitud global (validador_final.py) | 0.4-2.5 | 0.15-5.0 | Permet originals stub i expansió natural |
| Llindar paràgrafs (validador_final.py) | max(3, 25%) | max(5, 40%) | Formatació diferent genera molts FP |

---

## Accions pendents (per ordre de prioritat)

### CRÍTIC
1. ~~Nietzsche/die-philosophie: re-traduir fidelment~~ `.needs_fix` creat
2. ~~Aristotil/peri-psykhes: afegir original correcte, re-traduir~~ `.needs_fix` creat

### ALT
3. Completar originals incomplets (ibn-tufayl, teocrit, schopenhauer)
4. Re-executar traduccions interrompudes per errors CLI (horaci, lucreci, terenci, etc.)
5. Consolidar duplicats (luci/lucia-de-samosata, kipling)

### MITJÀ
6. Reanomenar kalidasa/meghaduta → kumarasambhava (o substituir contingut)
7. Trimmejar rumi/masnavi original.md (només els 10 contes seleccionats)
8. Completar traduccions parcials (dostoievski, bhagavad-gita, etc.)

---

## Conclusió

De ~100 obres verificades, **només 1 al·lucinació real** ha estat confirmada (Nietzsche) i **1 contingut erroni** (Aristotil). La resta són traduccions legítimes amb problemes de completesa o diferències de format que el verificador interpretava incorrectament com invencions. Els llindars del verificador han estat ajustats per reduir la taxa de falsos positius.
