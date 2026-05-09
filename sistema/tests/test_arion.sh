#!/bin/bash
# =============================================================================
# test_arion.sh — Suite de tests bàsics per Biblioteca Arion
# =============================================================================
set -uo pipefail
PASS=0; FAIL=0; SKIP=0

PROJECT="$HOME/biblioteca-universal-arion"
TASKS_DIR="$PROJECT/sistema/tasks"
MODULES_DIR="$PROJECT/sistema/automatitzacio/modules"

green() { echo -e "\033[32m$1\033[0m"; }
red()   { echo -e "\033[31m$1\033[0m"; }
yellow(){ echo -e "\033[33m$1\033[0m"; }

assert() {
    local desc="$1" expected="$2" actual="$3"
    if [ "$expected" = "$actual" ]; then
        green "  ✅ $desc"
        PASS=$((PASS + 1))
    else
        red "  ❌ $desc (expected='$expected', got='$actual')"
        FAIL=$((FAIL + 1))
    fi
}

assert_file() {
    local desc="$1" file="$2"
    if [ -f "$file" ]; then
        green "  ✅ $desc"
        PASS=$((PASS + 1))
    else
        red "  ❌ $desc (file not found: $file)"
        FAIL=$((FAIL + 1))
    fi
}

assert_dir() {
    local desc="$1" dir="$2"
    if [ -d "$dir" ]; then
        green "  ✅ $desc"
        PASS=$((PASS + 1))
    else
        red "  ❌ $dir (dir not found)"
        FAIL=$((FAIL + 1))
    fi
}

echo "═══════════════════════════════════════════"
echo "🧪 TESTS BIBLIOTECA ARION v6"
echo "═══════════════════════════════════════════"

# ── Estructura ───────────────────────────────────────────────────────────────
echo ""
echo "📁 Estructura de fitxers"
assert_dir "Directori projecte" "$PROJECT"
assert_dir "Mòduls" "$MODULES_DIR"
assert_dir "Tasques pending" "$TASKS_DIR/pending"
assert_dir "Tasques running" "$TASKS_DIR/running"
assert_dir "Tasques done" "$TASKS_DIR/done"
assert_dir "Tasques failed" "$TASKS_DIR/failed"
assert_dir "Logs" "$PROJECT/sistema/logs"

# ── Scripts principal ────────────────────────────────────────────────────────
echo ""
echo "📜 Scripts principals"
assert_file "Heartbeat.sh" "$PROJECT/sistema/automatitzacio/heartbeat.sh"
assert_file "Worker.sh" "$PROJECT/sistema/automatitzacio/worker.sh"
assert_file "Notificar.sh" "$PROJECT/sistema/automatitzacio/notificar.sh"

# ── Mòduls ──────────────────────────────────────────────────────────────────
echo ""
echo "📦 Mòduls del heartbeat"
for i in $(seq -w 1 10); do
    module=$(ls "$MODULES_DIR/${i}"-*.sh 2>/dev/null | head -1)
    if [ -n "$module" ]; then
        name=$(basename "$module")
        assert_file "$name" "$module"
    fi
done
assert_file "common.sh" "$MODULES_DIR/common.sh"

# ── Sintaxi bash ─────────────────────────────────────────────────────────────
echo ""
echo "🔤 Validació de sintaxi"
for script in "$PROJECT/sistema/automatitzacio/heartbeat.sh" \
             "$PROJECT/sistema/automatitzacio/worker.sh" \
             "$PROJECT/sistema/automatitzacio/notificar.sh" \
             "$MODULES_DIR"/*.sh; do
    [ -f "$script" ] || continue
    name=$(basename "$script")
    if bash -n "$script" 2>/dev/null; then
        green "  ✅ $name: sintaxi OK"
        PASS=$((PASS + 1))
    else
        red "  ❌ $name: ERROR de sintaxi"
        FAIL=$((FAIL + 1))
    fi
done

# ── Sintaxi Python ──────────────────────────────────────────────────────────
echo ""
echo "🐍 Validació Python"
for py in "$PROJECT/sistema/scripts/"*.py; do
    [ -f "$py" ] || continue
    name=$(basename "$py")
    if python3 -m py_compile "$py" 2>/dev/null; then
        green "  ✅ $name: sintaxi OK"
        PASS=$((PASS + 1))
    else
        red "  ❌ $name: ERROR de sintaxi"
        FAIL=$((FAIL + 1))
    fi
done

# ── Task Manager ────────────────────────────────────────────────────────────
echo ""
echo "📋 Task Manager"
TM="$PROJECT/sistema/scripts/task_manager.py"
if [ -f "$TM" ]; then
    stats=$(python3 "$TM" stats 2>/dev/null)
    assert "Task manager funciona" "0" "$(echo "$stats" | grep -c 'pending\|running\|done\|failed' | head -1)"
    
    # Test dedup
    hash1=$(python3 -c "import sys; sys.path.insert(0, '$PROJECT/sistema/scripts'); from task_manager import task_hash; print(task_hash('test', 'instrucció de prova'))" 2>/dev/null)
    hash2=$(python3 -c "import sys; sys.path.insert(0, '$PROJECT/sistema/scripts'); from task_manager import task_hash; print(task_hash('test', 'instrucció de prova'))" 2>/dev/null)
    assert "Hash determinista" "$hash1" "$hash2"
    
    hash3=$(python3 -c "import sys; sys.path.insert(0, '$PROJECT/sistema/scripts'); from task_manager import task_hash; print(task_hash('test', 'altra instrucció'))" 2>/dev/null)
    if [ "$hash1" != "$hash3" ]; then
        green "  ✅ Hash diferent per instrucció diferent"
        PASS=$((PASS + 1))
    else
        red "  ❌ Hash igual per instruccions diferents"
        FAIL=$((FAIL + 1))
    fi
fi

# ── Configuració ────────────────────────────────────────────────────────────
echo ""
echo "⚙️ Configuració"
assert_file "models.conf" "$PROJECT/sistema/config/models.conf"

# ── No codi mort ────────────────────────────────────────────────────────────
echo ""
echo "🧹 Codi mort"
tmp_count=$(find "$PROJECT/obres" -name ".tmp_*" -type f 2>/dev/null | wc -l)
assert "No .tmp files" "0" "$tmp_count"

backup_count=$(find "$PROJECT/sistema/automatitzacio" -name "*.backup" -type f 2>/dev/null | wc -l)
assert "No .backup files" "0" "$backup_count"

# ── Git ─────────────────────────────────────────────────────────────────────
echo ""
echo "📦 Git"
cd "$PROJECT"
assert "Git repo" "0" "$(git status --porcelain 2>/dev/null | wc -l)"
branch=$(git branch --show-current 2>/dev/null)
assert "Branch main" "main" "$branch"

# ── Resum ───────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════"
green "✅ PASS: $PASS"
if [ $FAIL -gt 0 ]; then red "❌ FAIL: $FAIL"; fi
echo "═══════════════════════════════════════════"

[ $FAIL -eq 0 ] && exit 0 || exit 1
