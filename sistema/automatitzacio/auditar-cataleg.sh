#!/bin/bash
# auditar-cataleg.sh — Audita totes les obres i genera informe + tasques de reparació
# Ús: bash sistema/automatitzacio/auditar-cataleg.sh [--fix]

set -uo pipefail
REPO="$HOME/biblioteca-universal-arion"
OBRES_DIR="$REPO/obres"
INFORME="$REPO/config/auditoria.json"
TASQUES_DIR="$HOME/.openclaw/workspace/tasks/pending"

# Comptadors
total=0; ok=0; problemes=0
declare -a RESULTATS=()

echo "🔍 Auditant catàleg..."

for obra_dir in "$OBRES_DIR"/*/*/*/; do
    [ -d "$obra_dir" ] || continue
    total=$((total + 1))

    autor=$(basename "$(dirname "$obra_dir")")
    obra=$(basename "$obra_dir")
    errors=()

    # 1. METADATA: existeix i és YAML vàlid?
    if [ ! -f "$obra_dir/metadata.yml" ]; then
        errors+=("NO_METADATA")
    else
        if ! python3 -c "import yaml; yaml.safe_load(open('$obra_dir/metadata.yml'))" 2>/dev/null; then
            errors+=("METADATA_INVALID")
        else
            # Comprovar camps obligatoris
            for camp in titol autor llengua_original categoria any_original; do
                if ! grep -q "$camp" "$obra_dir/metadata.yml" 2>/dev/null; then
                    errors+=("METADATA_FALTA_${camp^^}")
                fi
            done
            # Comprovar font_original amb URL
            if ! grep -q "font_original" "$obra_dir/metadata.yml" 2>/dev/null; then
                errors+=("NO_FONT_ORIGINAL_METADATA")
            elif ! grep -A2 "font_original" "$obra_dir/metadata.yml" | grep -q "http" 2>/dev/null; then
                errors+=("FONT_SENSE_URL")
            fi
        fi
    fi

    # 2. ORIGINAL: existeix i té contingut real (no placeholder)?
    if [ ! -f "$obra_dir/original.md" ]; then
        errors+=("NO_ORIGINAL")
    else
        chars=$(wc -c < "$obra_dir/original.md")
        if [ "$chars" -lt 500 ]; then
            errors+=("ORIGINAL_MASSA_CURT_${chars}c")
        fi
# Detectar contingut inventat o placeholder (patrons específics, no sub-cadenes)
        if grep -qE "(TODO|FIXME|PLACEHOLDER|PLACE_HOLDER):|<!-- TODO|<!-- PLACEHOLDER|\\[PLACEHOLDER\\]|\\[TODO\\]|^# TODO|^# FIXME|lorem ipsum|\\[text original\\]" "$obra_dir/original.md" 2>/dev/null; then
            errors+=("ORIGINAL_PLACEHOLDER")
        fi
    fi

    # 3. TRADUCCIÓ: existeix, té contingut, no és inventada?
    if [ ! -f "$obra_dir/traduccio.md" ]; then
        errors+=("NO_TRADUCCIO")
    else
        chars=$(wc -c < "$obra_dir/traduccio.md")
        if [ "$chars" -lt 500 ]; then
            errors+=("TRADUCCIO_MASSA_CURTA_${chars}c")
        fi
        # Proporció original/traducció (hauria de ser similar)
        if [ -f "$obra_dir/original.md" ]; then
            orig_chars=$(wc -c < "$obra_dir/original.md")
            trad_chars=$chars
            if [ "$orig_chars" -gt 0 ] && [ "$trad_chars" -gt 0 ]; then
                ratio=$((trad_chars * 100 / orig_chars))
                if [ "$ratio" -lt 30 ]; then
                    errors+=("TRADUCCIO_INCOMPLETA_${ratio}pct")
                fi
                if [ "$ratio" -gt 300 ]; then
                    errors+=("TRADUCCIO_INFLADA_${ratio}pct")
                fi
            fi
        fi
# Detectar contingut potencialment inventat (patrons específics, no sub-cadenes)
        if grep -qE "(TODO|FIXME|PLACEHOLDER|PLACE_HOLDER):|<!-- TODO|<!-- PLACEHOLDER|\\[PLACEHOLDER\\]|\\[TODO\\]|^# TODO|^# FIXME|lorem ipsum" "$obra_dir/traduccio.md" 2>/dev/null; then
            errors+=("TRADUCCIO_PLACEHOLDER")
        fi
    fi

    # 4. GLOSSARI: existeix i és YAML vàlid?
    if [ ! -f "$obra_dir/glossari.yml" ]; then
        errors+=("NO_GLOSSARI")
    else
        if ! python3 -c "import yaml; yaml.safe_load(open('$obra_dir/glossari.yml'))" 2>/dev/null; then
            errors+=("GLOSSARI_INVALID")
        fi
    fi

    # 5. NOTES: si existeix, comprovar format
    if [ -f "$obra_dir/notes.md" ]; then
        # Comprovar que les notes referenciades a traduccio.md existeixen a notes.md
        if [ -f "$obra_dir/traduccio.md" ]; then
            refs=$(grep -oP '\[\^(\d+)\]' "$obra_dir/traduccio.md" 2>/dev/null | sort -u | wc -l)
            notes=$(grep -c '^## \[' "$obra_dir/notes.md" 2>/dev/null || echo 0)
            if [ "$refs" -gt 0 ] && [ "$notes" -eq 0 ]; then
                errors+=("NOTES_REFERENCIADES_PERO_BUIDES")
            fi
        fi
    fi

    # 6. PORTADA: existeix i no és placeholder?
    if [ ! -f "$obra_dir/portada.png" ] && [ ! -f "$obra_dir/portada.jpg" ]; then
        errors+=("NO_PORTADA")
    else
        portada=$(ls "$obra_dir"/portada.{png,jpg} 2>/dev/null | head -1)
        if [ -n "$portada" ]; then
            size=$(stat -c%s "$portada" 2>/dev/null || stat -f%z "$portada" 2>/dev/null || echo 0)
            if [ "$size" -lt 5000 ]; then
                errors+=("PORTADA_PLACEHOLDER_${size}b")
            fi
        fi
    fi

    # 7. TRADUCCIO QUALITAT: castellanismes evidents
    if [ -f "$obra_dir/traduccio.md" ]; then
        if grep -qiP '\b(entonces|pues|sin embargo|mientras|además|también|pero|aunque|desde|hasta|hacia|según)\b' "$obra_dir/traduccio.md" 2>/dev/null; then
            errors+=("CASTELLANISMES_DETECTATS")
        fi
    fi

    # 8. FORMAT WEB: el build el detecta?
    if [ -f "$REPO/docs/api/works.json" ]; then
        if ! grep -q "$obra" "$REPO/docs/api/works.json" 2>/dev/null; then
            errors+=("NO_A_LA_WEB")
        fi
    fi

    # Resultat
    if [ ${#errors[@]} -eq 0 ]; then
        ok=$((ok + 1))
        status="✅"
    else
        problemes=$((problemes + 1))
        status="❌"
    fi

    # Guardar resultat (format JSON-like per processar després)
    error_list=$(IFS=','; echo "${errors[*]}")
    RESULTATS+=("{\"autor\":\"$autor\",\"obra\":\"$obra\",\"errors\":[\"${error_list//,/\",\"}\"],\"n_errors\":${#errors[@]}}")

    echo "$status $autor/$obra — ${#errors[@]} errors: ${error_list:-cap}"
done

echo ""
echo "════════════════════════════════════"
echo "📊 RESUM AUDITORIA"
echo "════════════════════════════════════"
echo "Total obres:    $total"
echo "✅ Correctes:   $ok"
echo "❌ Amb errors:  $problemes"
echo ""

# Guardar informe JSON
cat > "$INFORME" << JSONEOF
{
  "data": "$(date -Iseconds)",
  "total": $total,
  "correctes": $ok,
  "amb_errors": $problemes,
  "obres": [
    $(IFS=','; echo "${RESULTATS[*]}")
  ]
}
JSONEOF

echo "📄 Informe guardat a: $INFORME"

# Si --fix, generar tasques de reparació
if [[ "${1:-}" == "--fix" ]]; then
    echo ""
    echo "🔧 Generant tasques de reparació..."

    mkdir -p "$TASQUES_DIR"
    n_tasques=0

    # Obtenir llista de tasques ja existents (pending + running) per evitar duplicats
    EXISTING_TASKS=""
    for f in "$TASQUES_DIR"/*.json "$TASQUES_DIR/../running/"*.json; do
        [ -f "$f" ] && EXISTING_TASKS="$EXISTING_TASKS $(basename "$f")"
    done

    for r in "${RESULTATS[@]}"; do
        n_err=$(echo "$r" | grep -oP '"n_errors":\K\d+')
        [ "$n_err" -eq 0 ] && continue

        autor=$(echo "$r" | grep -oP '"autor":"\K[^"]+')
        obra=$(echo "$r" | grep -oP '"obra":"\K[^"]+')
        errs=$(echo "$r" | grep -oP '"errors":\[\K[^\]]+')

        # Prioritzar per gravetat
        priority=3
        [[ "$errs" == *"NO_ORIGINAL"* ]] || [[ "$errs" == *"NO_TRADUCCIO"* ]] && priority=1
        [[ "$errs" == *"INVENTAT"* ]] || [[ "$errs" == *"PLACEHOLDER"* ]] && priority=1
        [[ "$errs" == *"INCOMPLETA"* ]] && priority=2

        if [[ "$errs" == *"NO_ORIGINAL"* ]] || [[ "$errs" == *"ORIGINAL_MASSA_CURT"* ]] || [[ "$errs" == *"ORIGINAL_PLACEHOLDER"* ]]; then
            if ! echo "$EXISTING_TASKS" | grep -q "fix-fetch-${autor}-${obra}"; then
                task_id="fix-fetch-${autor}-${obra}-$(date +%s)"
                cat > "$TASQUES_DIR/${task_id}.json" << EOF
{
  "id": "$task_id",
  "type": "fix-fetch",
  "priority": $priority,
  "max_duration": 900,
  "instruction": "cd ~/biblioteca-universal-arion && python3 sistema/traduccio/cercador_fonts_v2.py --autor '$autor' --obra '$obra' --output obres/*/$autor/$obra/original.md && echo DONE",
  "created": "$(date -Iseconds)"
}
EOF
                n_tasques=$((n_tasques + 1))
            fi
        fi

        if [[ "$errs" == *"NO_METADATA"* ]] || [[ "$errs" == *"METADATA_INVALID"* ]] || [[ "$errs" == *"METADATA_FALTA"* ]] || [[ "$errs" == *"NO_FONT_ORIGINAL"* ]] || [[ "$errs" == *"FONT_SENSE_URL"* ]]; then
            if ! echo "$EXISTING_TASKS" | grep -q "fix-metadata-${autor}-${obra}"; then
                task_id="fix-metadata-${autor}-${obra}-$(date +%s)"
                cat > "$TASQUES_DIR/${task_id}.json" << EOF
{
  "id": "$task_id",
  "type": "fix-metadata",
  "priority": $priority,
  "max_duration": 600,
  "instruction": "cd ~/biblioteca-universal-arion && Revisa i completa el fitxer obres/*/$autor/$obra/metadata.yml. Ha de tenir TOTS els camps obligatoris: titol, autor, llengua_original, categoria, any_original. Si hi ha original.md, afegeix font_original amb la URL real d'on s'ha obtingut (Gutenberg, Wikisource, Perseus, etc). Si no saps la font, cerca-la. Valida que el YAML sigui correcte amb: python3 -c \"import yaml; yaml.safe_load(open('obres/*/$autor/$obra/metadata.yml'))\" && git add obres/*/$autor/$obra/metadata.yml && git commit -m 'fix: completar metadata $autor/$obra' && git push",
  "created": "$(date -Iseconds)"
}
EOF
                n_tasques=$((n_tasques + 1))
            fi
        fi

        if [[ "$errs" == *"NO_TRADUCCIO"* ]] || [[ "$errs" == *"TRADUCCIO_INCOMPLETA"* ]] || [[ "$errs" == *"TRADUCCIO_PLACEHOLDER"* ]]; then
            if ! echo "$EXISTING_TASKS" | grep -q "fix-translate-${autor}-${obra}"; then
                task_id="fix-translate-${autor}-${obra}-$(date +%s)"
                cat > "$TASQUES_DIR/${task_id}.json" << EOF
{
  "id": "$task_id",
  "type": "fix-translate",
  "priority": $priority,
  "max_duration": 3600,
  "instruction": "cd ~/biblioteca-universal-arion && Verifica que obres/*/$autor/$obra/original.md existeix i te contingut real. Si existeix, executa: python3 sistema/traduccio/traduir_pipeline.py --autor '$autor' --obra '$obra'. Si l'original no existeix, primer executa cercador_fonts_v2.py. Despres del pipeline, verifica que traduccio.md te contingut i fa sentit. git add -A obres/*/$autor/$obra/ && git commit -m 'fix: traduir/completar $autor/$obra' && git push",
  "created": "$(date -Iseconds)"
}
EOF
                n_tasques=$((n_tasques + 1))
            fi
        fi

        if [[ "$errs" == *"NO_GLOSSARI"* ]] || [[ "$errs" == *"GLOSSARI_INVALID"* ]]; then
            if ! echo "$EXISTING_TASKS" | grep -q "fix-glossari-${autor}-${obra}"; then
                task_id="fix-glossari-${autor}-${obra}-$(date +%s)"
                cat > "$TASQUES_DIR/${task_id}.json" << EOF
{
  "id": "$task_id",
  "type": "fix-glossari",
  "priority": 3,
  "max_duration": 600,
  "instruction": "cd ~/biblioteca-universal-arion && Revisa obres/*/$autor/$obra/glossari.yml. Si no existeix, crea'l a partir de original.md i traduccio.md amb els termes clau. Si existeix pero es invalid, corregeix el YAML. Valida amb: python3 -c \"import yaml; yaml.safe_load(open('obres/*/$autor/$obra/glossari.yml'))\" && git add obres/*/$autor/$obra/glossari.yml && git commit -m 'fix: glossari $autor/$obra' && git push",
  "created": "$(date -Iseconds)"
}
EOF
                n_tasques=$((n_tasques + 1))
            fi
        fi

        if [[ "$errs" == *"NO_PORTADA"* ]] || [[ "$errs" == *"PORTADA_PLACEHOLDER"* ]]; then
            if ! echo "$EXISTING_TASKS" | grep -q "fix-portada-${autor}-${obra}"; then
                task_id="fix-portada-${autor}-${obra}-$(date +%s)"
                cat > "$TASQUES_DIR/${task_id}.json" << EOF
{
  "id": "$task_id",
  "type": "fix-portada",
  "priority": 4,
  "max_duration": 600,
  "instruction": "cd ~/biblioteca-universal-arion && python3 sistema/traduccio/generar_portades.py --obra '$autor/$obra' && git add obres/*/$autor/$obra/portada.* && git commit -m 'fix: portada $autor/$obra' && git push",
  "created": "$(date -Iseconds)"
}
EOF
                n_tasques=$((n_tasques + 1))
            fi
        fi

        if [[ "$errs" == *"CASTELLANISMES"* ]]; then
            if ! echo "$EXISTING_TASKS" | grep -q "fix-llengua-${autor}-${obra}"; then
                task_id="fix-llengua-${autor}-${obra}-$(date +%s)"
                cat > "$TASQUES_DIR/${task_id}.json" << EOF
{
  "id": "$task_id",
  "type": "fix-llengua",
  "priority": 2,
  "max_duration": 1800,
  "instruction": "cd ~/biblioteca-universal-arion && Obre obres/*/$autor/$obra/traduccio.md i corregeix tots els castellanismes i anglicismes. Revisa especialment: entonces->aleshores/llavors, pues->doncs, sin embargo->tanmateix/no obstant, mientras->mentre, ademas->a mes, tambien->tambe, pero->pero, aunque->tot i que/malgrat que, desde->des de, hasta->fins a, hacia->cap a, segun->segons. Revisa tambe la normativa IEC. git add obres/*/$autor/$obra/traduccio.md && git commit -m 'fix: corregir castellanismes $autor/$obra' && git push",
  "created": "$(date -Iseconds)"
}
EOF
                n_tasques=$((n_tasques + 1))
            fi
        fi

        if [[ "$errs" == *"NOTES_REFERENCIADES_PERO_BUIDES"* ]]; then
            if ! echo "$EXISTING_TASKS" | grep -q "fix-notes-${autor}-${obra}"; then
                task_id="fix-notes-${autor}-${obra}-$(date +%s)"
                cat > "$TASQUES_DIR/${task_id}.json" << EOF
{
  "id": "$task_id",
  "type": "fix-notes",
  "priority": 3,
  "max_duration": 1200,
  "instruction": "cd ~/biblioteca-universal-arion && Obre obres/*/$autor/$obra/traduccio.md i obres/*/$autor/$obra/notes.md. Verifica que cada referencia [^N] a la traduccio te la nota corresponent ## [N] a notes.md. Si falten notes, genera-les amb context adequat. Si les referencies son incorrectes, arregla la numeracio. git add obres/*/$autor/$obra/{traduccio.md,notes.md} && git commit -m 'fix: notes $autor/$obra' && git push",
  "created": "$(date -Iseconds)"
}
EOF
                n_tasques=$((n_tasques + 1))
            fi
        fi

        if [[ "$errs" == *"NO_A_LA_WEB"* ]]; then
            if ! echo "$EXISTING_TASKS" | grep -q "fix-web-${autor}-${obra}"; then
                task_id="fix-web-${autor}-${obra}-$(date +%s)"
                cat > "$TASQUES_DIR/${task_id}.json" << EOF
{
  "id": "$task_id",
  "type": "fix-web",
  "priority": 3,
  "max_duration": 300,
  "instruction": "cd ~/biblioteca-universal-arion && python3 sistema/web/build.py && git add docs/ && git commit -m 'build: afegir $autor/$obra a la web' && git push",
  "created": "$(date -Iseconds)"
}
EOF
                n_tasques=$((n_tasques + 1))
            fi
        fi
    done

    echo "✅ $n_tasques tasques de reparació creades a: $TASQUES_DIR"
fi
