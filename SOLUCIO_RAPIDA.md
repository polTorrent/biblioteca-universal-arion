# ⚡ SOLUCIÓ RÀPIDA - Editorial Clàssica

## ✅ Problema Arreglat!

Els paths dels fitxers CSS i JS ara són **relatius** i funcionen correctament.

---

## 🚀 Com Veure-ho ARA (3 opcions)

### Opció 1: Script Automàtic ⭐ MÉS FÀCIL

```bash
bash scripts/serve.sh
```

T'oferirà 3 opcions:
1. Servidor Python (recomanat)
2. Obrir directament
3. Mostrar path

---

### Opció 2: Servidor Python 🐍 RECOMANAT

```bash
cd docs
python3 -m http.server 8000
```

Després obre el navegador a:
```
http://localhost:8000
```

**Per aturar**: `Ctrl+C`

---

### Opció 3: Obrir Directament

**Des de WSL2:**
```bash
explorer.exe docs/index.html
```

**Des de Linux:**
```bash
xdg-open docs/index.html
```

**Des de Mac:**
```bash
open docs/index.html
```

---

## 🧪 Test Ràpid

Executa això per verificar que tot funciona:

```bash
# 1. Reconstruir (si cal)
python3 scripts/build.py

# 2. Verificar fitxers
ls -lh docs/*.html docs/css/ docs/js/

# 3. Servir
cd docs && python3 -m http.server 8000
```

Després visita: http://localhost:8000

---

## ✅ Què hauries de veure

Quan obris http://localhost:8000:

1. ✅ **Pàgina principal** amb colors i fonts bonics
2. ✅ **Botó de dark mode** (🌙) al header
3. ✅ **Cerca** funcional al hero section
4. ✅ **Filtres** (llengua, gènere, estat)
5. ✅ **Estadístiques** amb fons graduat
6. ✅ **Obra del Banquet** a la llista

Quan cliquis a "El Banquet":

1. ✅ **Títol i metadades** ben formatades
2. ✅ **TOC lateral** generada automàticament
3. ✅ **Diàlegs** amb parlants en negreta
4. ✅ **Notes del traductor** destacades
5. ✅ **Glossari** al final
6. ✅ **Bibliografia** estructurada

---

## 🐛 Si encara tens problemes

1. **Reconstrueix tot**:
   ```bash
   python3 scripts/build.py --clean
   ```

2. **Verifica paths relatius**:
   ```bash
   grep 'href="css/\|src="js/' docs/index.html
   # Ha de mostrar: href="css/styles.css" i src="js/app.js"
   ```

3. **Consulta troubleshooting**:
   - Llegeix [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

4. **Errors del navegador**:
   - Obre http://localhost:8000
   - Prem `F12`
   - Ves a "Console"
   - Busca errors en vermell

---

## 📝 Comandes Ràpides

```bash
# Build
python3 scripts/build.py

# Build + Clean
python3 scripts/build.py --clean

# Servir
bash scripts/serve.sh
# O
cd docs && python3 -m http.server 8000

# Una obra específica
python3 scripts/build.py obres/plato-banquet-exemple.md
```

---

## 🎉 Gaudeix!

Si tot funciona, hauries de veure una **web professional** amb:
- Disseny responsive
- Dark mode
- TOC dinàmica
- Cerca d'obres
- Filtres
- I molt més!

---

**Path dels fitxers generats**: `docs/`

**Documentació completa**:
- [WEB_SETUP.md](WEB_SETUP.md) - Guia d'ús
- [FORMAT.md](FORMAT.md) - Format de traduccions
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Resolució de problemes

---

**Data**: 2026-01-25
**Versió**: 1.1 (paths relatius)
**Estat**: ✅ **ARREGLAT I FUNCIONAL**
