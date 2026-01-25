# 🔧 Troubleshooting - Editorial Clàssica

## Problema: "No se puede conectar"

### Causa
Els paths dels fitxers CSS i JS eren absoluts (`/css/styles.css`) i no funcionaven quan s'obria l'HTML directament.

### Solució Aplicada ✅
S'ha actualitzat `scripts/build.py` per generar paths relatius (`css/styles.css`).

---

## Com Veure l'HTML Generat

### Opció 1: Obrir Directament (MÉS FÀCIL) ⭐

**Des de WSL2:**
```bash
# Obre amb el navegador per defecte de Windows
explorer.exe docs/index.html
```

**Des de Linux/Mac:**
```bash
# Linux
xdg-open docs/index.html

# Mac
open docs/index.html
```

**Manualment:**
1. Copia el path: `realpath docs/index.html`
2. Obre'l al navegador

---

### Opció 2: Servidor Python (RECOMANAT) 🐍

```bash
cd docs
python3 -m http.server 8000
```

Després obre el navegador:
```
http://localhost:8000
```

**Aturar el servidor**: `Ctrl+C`

---

### Opció 3: Servidor PHP

```bash
cd docs
php -S localhost:8000
```

Obre: `http://localhost:8000`

---

### Opció 4: Live Server (VSCode)

Si uses Visual Studio Code:

1. Instal·la l'extensió "Live Server"
2. Click dret a `docs/index.html`
3. "Open with Live Server"

---

## Verificar que Tot Funciona

### 1. Verificar fitxers existeixen

```bash
ls -lh docs/
# Hauries de veure:
# - index.html
# - plato-banquet-exemple.html
# - css/styles.css
# - js/app.js
```

### 2. Verificar paths són relatius

```bash
grep 'href="css/\|src="js/' docs/index.html
# Ha de mostrar:
# href="css/styles.css"
# src="js/app.js"
```

### 3. Verificar CSS es carrega

Obre `docs/index.html` al navegador i:
- Prem `F12` (Developer Tools)
- Ves a la pestanya "Network"
- Refresca la pàgina (`F5`)
- Verifica que `styles.css` es carrega (status 200)

---

## Problemes Comuns

### Error: "CSS/JS no es carrega"

**Causa**: Paths incorrectes

**Solució**:
```bash
# Reconstruir
python3 scripts/build.py --clean

# Verificar paths
grep 'href="' docs/index.html | grep css
```

### Error: "Port 8000 ja en ús"

**Solució**: Usa un altre port
```bash
python3 -m http.server 8001
# Obre http://localhost:8001
```

### Error: "python: command not found"

**Solució**: Usa `python3`
```bash
python3 scripts/build.py
cd docs
python3 -m http.server 8000
```

### Error: Fonts de Google no carreguen

**Causa**: Sense connexió a internet

**Solució**: Les fonts són opcionals, el CSS funciona igualment

---

## Rebuild Ràpid

Si has canviat alguna cosa:

```bash
# Neteja i reconstrueix
python3 scripts/build.py --clean

# O només reconstrueix
python3 scripts/build.py
```

---

## Debug Mode

Activa debug per veure més informació:

```bash
# Edita scripts/build.py i afegeix prints
# O mira els errors al navegador (F12 → Console)
```

---

## WSL2 Específic

### Accedir des de Windows

**Opció A**: Obre amb explorer
```bash
explorer.exe docs/index.html
```

**Opció B**: Servidor local
```bash
cd docs
python3 -m http.server 8000
# Obre a Windows: http://localhost:8000
```

**Opció C**: Path de WSL a Windows
```
\\wsl$\Ubuntu\root\editorial-classica\docs\index.html
```

---

## Verificació Final

Tot funciona si veus:
- ✅ Pàgina amb estils (colors, fonts)
- ✅ Navegació funciona
- ✅ Dark mode toggle funciona (🌙 botó)
- ✅ TOC lateral es genera
- ✅ Obra del Banquet es mostra correctament

---

## Encara no Funciona?

1. **Reconstrueix tot**:
   ```bash
   python3 scripts/build.py --clean
   ```

2. **Verifica permisos**:
   ```bash
   chmod -R 755 docs/
   ```

3. **Prova amb un HTML mínim**:
   ```bash
   echo '<!DOCTYPE html><html><head><link rel="stylesheet" href="css/styles.css"></head><body><h1>Test</h1></body></html>' > docs/test.html
   explorer.exe docs/test.html
   ```

4. **Consulta el navegador**:
   - Prem `F12`
   - Ves a "Console"
   - Busca errors en vermell

---

## Contacte

Si res funciona, comparteix:
- Sistema operatiu
- Comanda executada
- Error exacte
- Captura de pantalla de F12 → Console

---

**Data**: 2026-01-25
**Versió**: 1.1 (paths relatius)
