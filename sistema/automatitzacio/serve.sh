#!/bin/bash
# Script per servir Editorial Clàssica localment

echo "🌐 Editorial Clàssica - Servidor Local"
echo "======================================"
echo ""

# Verificar que docs/ existeix
if [ ! -d "docs" ]; then
    echo "❌ Directori docs/ no trobat!"
    echo "Executa primer: python3 scripts/build.py"
    exit 1
fi

# Comptar fitxers HTML
html_count=$(find docs -name "*.html" | wc -l)
echo "📄 Fitxers HTML trobats: $html_count"
echo ""

# Mostrar opcions
echo "Tria com veure-ho:"
echo ""
echo "1️⃣  Servidor Python (recomanat)"
echo "2️⃣  Obrir directament amb navegador"
echo "3️⃣  Mostrar path del fitxer"
echo ""
read -p "Opció [1/2/3]: " choice

case $choice in
    1)
        echo ""
        echo "🚀 Iniciant servidor a http://localhost:8000"
        echo "   Prem Ctrl+C per aturar"
        echo ""
        cd docs
        python3 -m http.server 8000
        ;;
    2)
        echo ""
        echo "🌐 Obrint al navegador..."
        if command -v explorer.exe &> /dev/null; then
            # WSL2
            explorer.exe docs/index.html
        elif command -v xdg-open &> /dev/null; then
            # Linux
            xdg-open docs/index.html
        elif command -v open &> /dev/null; then
            # Mac
            open docs/index.html
        else
            echo "❌ No s'ha pogut obrir automàticament"
            echo "Obre manualment: $(realpath docs/index.html)"
        fi
        ;;
    3)
        echo ""
        echo "📁 Path complet:"
        realpath docs/index.html
        echo ""
        echo "Copia aquest path i obre'l al navegador"
        ;;
    *)
        echo "❌ Opció no vàlida"
        exit 1
        ;;
esac
