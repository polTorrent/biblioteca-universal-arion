#!/usr/bin/env bash
# claude-dev-guard.sh — Hook PreToolUse del worker de desenvolupament autònom.
#
# Rep la crida d'eina a $CLAUDE_TOOL_INPUT (JSON). Bloqueja ordres
# destructives o que toquin secrets/xarxa. Sortir amb codi 2 bloqueja la crida.
set -u

INPUT="${CLAUDE_TOOL_INPUT:-}"
if [ -z "$INPUT" ] && [ ! -t 0 ]; then
    INPUT="$(cat 2>/dev/null || true)"
fi

PATTERNS=(
    'git[[:space:]]+push'
    'git[[:space:]]+[^|]*--force'
    'git[[:space:]]+reset[[:space:]]+--hard'
    'git[[:space:]]+clean[[:space:]]+-[a-z]*f'
    'rm[[:space:]]+-[a-zA-Z]*r[a-zA-Z]*[[:space:]]+/'
    'rm[[:space:]]+-[a-zA-Z]*r[a-zA-Z]*[[:space:]]+~'
    'rm[[:space:]]+-[a-zA-Z]*f[a-zA-Z]*[[:space:]]+/(home|etc|usr|var)'
    ':\(\)[[:space:]]*\{'
    'curl[[:space:]][^|]*\|[[:space:]]*(ba)?sh'
    'wget[[:space:]][^|]*\|[[:space:]]*(ba)?sh'
    '>\s*[^ ]*\.env'
    'sk-ant-'
    'ghp_'
    'chmod[[:space:]]+777'
    'sudo[[:space:]]'
)

for p in "${PATTERNS[@]}"; do
    if printf '%s' "$INPUT" | grep -qE "$p"; then
        echo "⛔ Guard: crida bloquejada (coincideix amb '$p')." >&2
        exit 2
    fi
done
exit 0
