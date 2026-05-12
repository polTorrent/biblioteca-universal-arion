#!/usr/bin/env python3
import json, os, sys, re, subprocess

V = os.environ.get("VENICE_API_KEY", "")
U = "https://api.venice.ai/api/v1/chat/completions"

# Comandes bash vàlides (no incloem paraules que poden aparèixer en text descriptiu)
VALID_BASH_CMDS = {'python3', 'git', 'echo', 'cat', 'cp', 'mv', 'mkdir', 'rm', 'find',
                   'grep', 'sed', 'awk', 'head', 'tail', 'jq', 'ls', 'touch', 'chmod',
                   'ln', 'date', 'wc', 'sort', 'uniq', 'diff', 'patch', 'tar', 'curl'}

def vc(prompt, model="claude-opus-4-7", system="Ets un assistent per Biblioteca Arion.", max_tokens=2000):
    import urllib.request, json as j
    body = j.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "venice_parameters": {"disable_thinking": True, "strip_thinking_response": True}
    }).encode("utf-8")
    req = urllib.request.Request(U, data=body, headers={
        "Authorization": f"Bearer {V}",
        "Content-Type": "application/json"
    }, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = j.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"].get("content", "") or ""
            # Fallback: si thinking ha menjat el content, usar reasoning
            if not content.strip():
                content = data["choices"][0]["message"].get("reasoning_content", "") or ""
            return content
    except Exception as e:
        print(f"Error Venice: {e}", file=sys.stderr)
        return None

def is_valid_bash_line(line):
    '''Comprova si una línia és realment bash executable'''
    stripped = line.strip()
    if not stripped:
        return False
    # Extreure nom de comanda (ignorant variables env, cd al principi)
    cleaned = re.sub(r'^[A-Z_][A-Z0-9_]*=\S+\s+', '', stripped)  # VAR=value cmd
    cleaned = re.sub(r'^cd\s+\S+\s*&&\s*', '', cleaned)  # cd X &&
    cleaned = re.sub(r'^cd\s+\S+\s*;\s*', '', cleaned)   # cd X ;
    cmd = cleaned.split()[0] if cleaned.split() else ""
    # Si la comanda és una paraula catalana/descriptiva, no és bash
    if cmd and (cmd[0].isupper() or cmd in {'revisa', 'completa', 'afegeix', 'verifica',
                                             'cerca', 'busca', 'mira', 'revisa'}):
        return False
    return cmd in VALID_BASH_CMDS or any(stripped.startswith(x) for x in VALID_BASH_CMDS)

def extract_bash_from_instruction(inst):
    # Buscar blocs ```bash ... ``` primer (això té prioritat)
    blocks = re.findall(r'```(?:bash)?\s*\n(.*?)\n```', inst, re.DOTALL)
    if blocks:
        return '\n'.join(blocks)
    # Buscar línies executable bash
    lines = inst.split('\n')
    bash_lines = []
    for line in lines:
        stripped = line.strip()
        if is_valid_bash_line(stripped):
            bash_lines.append(stripped)
    if bash_lines:
        return '\n'.join(bash_lines)
    return None

def main():
    if len(sys.argv) < 2:
        print("Us: python3 hermes_task_executor.py <fitxer>")
        sys.exit(1)
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        task = json.load(f)
    ttype = task.get("type", "unknown")
    inst = task.get("instruction", "")
    model = task.get("model", "claude-opus-4-7")
    print(f"Tasca: {ttype}")
    print(f"Model: {model}")
    bc = extract_bash_from_instruction(inst)
    if bc:
        print(f"Executant bash:")
        print(f"  {bc[:200]}...")
        r = subprocess.run(bc, shell=True, capture_output=True, text=True, timeout=1800,
                           cwd=os.environ.get("HOME", "") + "/biblioteca-universal-arion")
        if r.returncode == 0:
            print("Completat")
            if r.stdout:
                print(r.stdout[:500])
            sys.exit(0)
        else:
            print(f"Error: {r.stderr[:500]}")
            sys.exit(1)
    print("Generant accions amb Venice AI...")
    resp = vc(inst, model=model, system="Ets un executor automatic per a Biblioteca Arion. Respon UNICAMENT amb blocs de codi bash executables. No afegeixis explicacions.")
    if not resp:
        print("Error: no resposta de Venice")
        sys.exit(1)
    bc = extract_bash_from_instruction(resp)
    if not bc:
        print("Error: no comandes bash a la resposta")
        print(resp[:500])
        sys.exit(1)
    print("Executant bash generat")
    r = subprocess.run(bc, shell=True, capture_output=True, text=True, timeout=1800,
                       cwd=os.environ.get("HOME", "") + "/biblioteca-universal-arion")
    if r.returncode == 0:
        print("Completat")
        if r.stdout:
            print(r.stdout[:500])
        sys.exit(0)
    else:
        print(f"Error: {r.stderr[:500]}")
        sys.exit(1)

if __name__ == "__main__":
    main()
