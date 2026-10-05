#!/usr/bin/env python3
"""
quota-probe.py — Detecta si la subscripció Claude (Pro) té quota lliure.

Fa una prova mínima (1 torn, sense eines, sense persistir sessió) i classifica
la resposta. Escriu l'estat a state/quota.json i imprimeix una línia JSON.

Codis de sortida:
    0  → FREE   (quota disponible)
    10 → LIMIT  (límit de la subscripció assolit)
    2  → ERROR  (auth, xarxa, binari...)
"""
import datetime
import json
import os
import pathlib
import re
import subprocess
import sys

DEV_DIR = pathlib.Path(__file__).resolve().parent
STATE = DEV_DIR / "state"
STATE.mkdir(parents=True, exist_ok=True)
QUOTA = STATE / "quota.json"
RAW = STATE / "quota_raw.txt"

NODE_BIN = os.path.expanduser("~/.nvm/versions/node/v24.13.0/bin")

env = dict(os.environ)
env["PATH"] = NODE_BIN + ":" + env.get("PATH", "")
env.pop("CLAUDECODE", None)  # evita l'error "nested sessions"

timeout = int(os.environ.get("QUOTA_PROBE_TIMEOUT", "90"))
model = os.environ.get("QUOTA_PROBE_MODEL", "haiku")

cmd = [
    "claude", "-p", "Respon només amb la paraula: PING",
    "--model", model,
    "--max-turns", "1",
    "--tools", "",
    "--no-session-persistence",
    "--output-format", "json",
]

now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
status, reason, reset, cost, rc = "ERROR", "", "", None, None
txt = ""

try:
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
    rc = p.returncode
    txt = (p.stdout or "") + "\n" + (p.stderr or "")
except subprocess.TimeoutExpired as e:
    rc = 124
    out = e.stdout or b""
    txt = out.decode(errors="replace") if isinstance(out, bytes) else str(out)
except FileNotFoundError:
    rc = 127
    txt = "claude no trobat al PATH"

RAW.write_text(txt, encoding="utf-8", errors="replace")

obj = None
try:
    obj = json.loads(txt.strip())
except Exception:
    m = re.search(r"\{.*\}\s*$", txt, re.S)
    if m:
        try:
            obj = json.loads(m.group(0))
        except Exception:
            obj = None

if obj is not None:
    is_err = obj.get("is_error")
    sub = str(obj.get("subtype", ""))
    res = str(obj.get("result", ""))
    api = str(obj.get("api_error_status"))
    cost = obj.get("total_cost_usd")
    if (not is_err) and sub == "success":
        status, reason = "FREE", "prova correcta"
    else:
        blob = (res + " " + sub + " " + api).lower()
        status = "LIMIT" if any(k in blob for k in ("limit", "429", "quota")) else "ERROR"
        reason = res[:280] or sub
else:
    low = txt.lower()
    if any(k in low for k in ("usage limit", "rate limit", "limit reached",
                              "resets at", "429", "quota")):
        status = "LIMIT"
    elif rc == 124:
        reason = "timeout"
    elif rc == 127:
        reason = "claude no trobat"
    reason = reason or txt.strip()[:280]

if status == "LIMIT" and not reset:
    m = re.search(r"reset[s]?\s+(at\s+)?[^\n\.]+", reason or txt, re.I)
    if m:
        reset = m.group(0).strip()

out = {
    "status": status,
    "reason": reason,
    "reset": reset,
    "rc": rc,
    "ts": now,
    "cost": cost,
    "model": model,
}
QUOTA.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False))
sys.exit({"FREE": 0, "LIMIT": 10, "ERROR": 2}.get(status, 2))
