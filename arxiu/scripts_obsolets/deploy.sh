#!/bin/bash
# Deploy automàtic a GitHub Pages

echo "🚀 Deploy Editorial Clàssica"
echo "============================"

# 1. Regenerar web
echo "📦 Generant web..."
python3 sistema/web/build.py --clean

# 2. Verificar canvis
echo ""
echo "🔍 Verificant canvis..."
git status --short

# 3. Afegir tots els canvis
git add .

# 4. Commit amb data/hora
DATA=$(date +"%Y-%m-%d %H:%M")
read -p "Missatge del commit (o Enter per defecte): " MSG
if [ -z "$MSG" ]; then
    MSG="Actualització $DATA"
fi

echo ""
echo "📝 Commit: $MSG"
git commit -m "$MSG

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

# 5. Push a GitHub
echo ""
echo "⬆️ Pujant a GitHub..."
git push

echo ""
echo "✅ Deploy completat!"
echo "🌐 Web: https://poltorrent.github.io/editorial-classica/"
echo "⏱️ Espera 1-2 minuts per veure els canvis"
