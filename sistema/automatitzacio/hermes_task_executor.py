#!/usr/bin/env python3
"""
Executor automàtic per a tasques de fix-* de Biblioteca Arion.
Processa prompts en natural generant scripts bash i executant-los.
Requereix VENICE_API_KEY a l'entorn.
"""
import json, os, sys, re, subprocess, yaml

VENICE_API_KEY = os.getenv("VENICE_API_KEY", "")
VENICE_URL = "https://api.venice.ai/api/v1/chat/completions"

def venice_chat(prompt, model="zai-org-glm-5", system="Ets un assistent per Biblioteca Arion.", max_tokens=2000):
    import urllib.request, json as json_mod
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "venice_parameters": {"disable_system_prompt": True}
    }
    req = urllib.request.Request(
        VENICE_URL,
        data=json_mod.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {VENICE_API_KEY}", "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json_mod.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Error Venice: {e}", file=sys.stderr)
        return None

def extract_bash_from_instruction(instruction):
    """
    Extreure blocs de codi bash de prompts complexos.
    Si no hi ha blocs de codi, intenta trobar la part executable.
    """
    # Buscar blocs ```bash ... ``` o ``` ... ```
    bash_blocks = re.findall(r'```(?:bash)?\s*\n(.*?)\n```', instruction, re.DOTALL)
    if bash_blocks:
        return '\n'.join(bash_blocks)

    # Buscar línies que comencin amb comandes típiques
    lines = instruction.split('\n')
    bash_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('cd ') or stripped.startswith('python3 ') or stripped.startswith('git ') or stripped.startswith('echo ') or stripped.startswith('cat ') or stripped.startswith('cp ') or stripped.startswith('mv ') or stripped.startswith('mkdir ') or stripped.startswith('rm '):
            bash_lines.append(stripped)

    if bash_lines:
        return '\n'.join(bash_lines)

    return None

def generate_bash_from_prompt(task_type, instruction, obra_path):
    """
    Per a prompts en natural (fix-metadata, fix-glossari, fix-portada),
    generar un script bash executable via Venice LLM.
    """
    system = """Ets un assistent tècnic de Biblioteca Arion.
Respon EXCLUSIVAMENT amb un script bash executable, sense explicacions.
El script ha de:
1. Treballar dins del directori del projecte
2. No fer push a git automàticament (deixa-ho comentat)
3. Validar resultats abans de continuar
4. Retornar exit 0 si tot OK, exit 1 si hi ha errors
"""
    prompt = f"""Genera un script bash executable per a aquesta tasca de Biblioteca Arion:

TIPUS: {task_type}
OBRA: {obra_path}
INSTRUCCIONS:
{instruction}

Respon NOMÉS amb el script bash, sense markdown, sense explicacions.
Comença amb #!/bin/bash i acaba amb exit 0 o exit 1.
"""
    response = venice_chat(prompt, system=system, max_tokens=2000)
    if not response:
        return None

    # Netejar markdown del voltant
    response = response.strip()
    if response.startswith("```"):
        response = re.sub(r'^```(?:bash)?\s*\n', '', response)
        response = re.sub(r'\n```\s*$', '', response)

    return response.strip()

def auto_fix_metadata(obra_path):
    """
    Versió automàtica sense LLM per fix-metadata.
    Completa camps bàsics si falten.
    """
    import yaml, os
    metadata_path = os.path.join(obra_path, "metadata.yml")
    if not os.path.exists(metadata_path):
        return False, "metadata.yml no existeix"

    try:
        with open(metadata_path) as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        return False, f"Error llegint YAML: {e}"

    modified = False
    # Camps obligatoris per defecte
    defaults = {
        "titol": os.path.basename(obra_path).replace("-", " ").title(),
        "autor": "Desconegut",
        "llengua_original": "llatí",
        "categoria": os.path.basename(os.path.dirname(obra_path)) if os.path.dirname(obra_path) else "desconeguda",
        "any_original": "Desconegut"
    }

    for key, val in defaults.items():
        if key not in data or not data.get(key):
            data[key] = val
            modified = True

    # Intentar extreure font_original de l'original.md si existeix
    original_path = os.path.join(obra_path, "original.md")
    if os.path.exists(original_path) and ("font_original" not in data or not data.get("font_original")):
        with open(original_path) as f:
            first_lines = ''.join(f.readline() for _ in range(10))
        # Buscar URL als primers comentaris
        urls = re.findall(r'(https?://[^\s\)]+)', first_lines)
        if urls:
            data["font_original"] = urls[0]
            modified = True
        else:
            data["font_original"] = "No especificada"
            modified = True

    if modified:
        with open(metadata_path, 'w') as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)
        return True, "Metadata completada automàticament"
    return True, "Metadata ja completa"

def run_task(task_file):
    with open(task_file) as f:
        task = json.load(f)

    task_type = task.get("type", "")
    instruction = task.get("instruction", "")
    obra = task.get("obra", "")
    project_dir = os.path.expanduser("~/biblioteca-universal-arion")

    # Determinar ruta de l'obra
    obra_path = obra if obra else os.path.join(project_dir, re.search(r'obres/[a-z0-9/_/-]+', instruction).group(0) if re.search(r'obres/[a-z0-9/_/-]+', instruction) else "")

    print(f"[EXECUTOR] Tasca: {task_type} -> {obra_path}")

    # === fix-translate o fix-fetch: extreure bash del prompt ===
    if task_type in ("fix-translate", "fix-fetch"):
        bash_script = extract_bash_from_instruction(instruction)
        if bash_script:
            print(f"[EXECUTOR] Bash extret ({len(bash_script)} chars)")
            result = subprocess.run(["bash", "-c", f"cd {project_dir} && {bash_script}"], capture_output=True, text=True, timeout=1800)
            print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            return result.returncode
        else:
            print("[EXECUTOR] No s'ha pogut extreure bash del prompt")
            return 1

    # === fix-metadata: intentar automàtic primer ===
    if task_type == "fix-metadata":
        ok, msg = auto_fix_metadata(obra_path)
        if ok:
            print(f"[EXECUTOR] {msg}")
            # Intentar git add si hi ha canvis
            subprocess.run(["git", "add", os.path.join(obra_path, "metadata.yml")], cwd=project_dir, capture_output=True)
            return 0
        print(f"[EXECUTOR] Auto-fix metadata fallit: {msg}")
        # Fallback a LLM

    # === fix-metadata, fix-glossari, fix-portada: generar bash via LLM ===
    if task_type in ("fix-metadata", "fix-glossari", "fix-portada"):
        print("[EXECUTOR] Generant script via Venice LLM...")
        bash_script = generate_bash_from_prompt(task_type, instruction, obra_path)
        if not bash_script:
            print("[EXECUTOR] No s'ha pogut generar script")
            return 1

        print(f"[EXECUTOR] Script generat ({len(bash_script)} chars)")
        print("---SCRIPT---")
        print(bash_script)
        print("---FI SCRIPT---")

        result = subprocess.run(["bash", "-c", f"cd {project_dir} && {bash_script}"], capture_output=True, text=True, timeout=600)
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode

    # === Default: intentar bash directe ===
    print("[EXECUTOR] Executant com a bash directe...")
    result = subprocess.run(["bash", "-c", f"cd {project_dir} && {instruction}"], capture_output=True, text=True, timeout=600)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Ús: python3 hermes_task_executor.py <tasca.json>", file=sys.stderr)
        sys.exit(1)
    sys.exit(run_task(sys.argv[1]))
