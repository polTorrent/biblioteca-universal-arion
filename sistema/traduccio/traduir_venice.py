#!/usr/bin/env python3
"""Traducció avançada amb Venice AI per obres de Biblioteca Arion.

Millores v2.2:
- Thinking selectiu per tasca (models.conf: thinking=on/off)
- Parser robust de <thinking> tags + reasoning_content
- Retry automàtic si output buit
- Validació de ratio longitud (0.6x-1.8x)
- Mètriques JSON per traducció
- Prompt reforçat amb cites establertes

Ús:
    python3 sistema/traduccio/traduir_venice.py --autor aristotil --obra peri-psykhes
    python3 sistema/traduccio/traduir_venice.py --ruta obres/filosofia/aristotil/peri-psykhes/
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Constants
VENICE_SCRIPT = Path.home() / ".hermes" / "skills" / "openclaw-imports" / "venice-ai" / "scripts" / "venice.py"
DEFAULT_MODEL = "claude-sonnet-4-6"
CHUNK_SIZE = 1000  # Caràcters per chunk
MAX_RETRIES = 3
VENICE_TIMEOUT = 300
API_BASE = "https://api.venice.ai/api/v1"
USER_AGENT = "BibliotecaArion/2.2"

# Model segons gènere (fallback)
GENRE_MODELS = {
    "filosofia": "claude-opus-4-7",
    "poesia": "claude-opus-4-7",
    "teatre": "claude-opus-4-7",
    "narrativa": "claude-sonnet-4-6",
    "assaig": "claude-sonnet-4-6",
    "oriental": "qwen3-235b-a22b-instruct-2507",
}

# Mapeig de models antics a noms actuals de Venice
MODEL_ALIASES = {
    "glm-5": "zai-org-glm-5",
    "glm-5-1": "zai-org-glm-5-1",
}

# System prompts per gènere (especialitzats)
SYSTEM_PROMPTS = {
    "filosofia": (
        "Tradueix al català literari estàndard. Mantén el registre i ritme de l'original. "
        "Per a frases canòniques o cites cèlebres, usa la traducció catalana establerta si existeix "
        "(ex: Hamlet → Salvador Oliva). En filosofia, prioritza la precisió terminològica i la claredat argumentativa."
    ),
    "poesia": (
        "Tradueix al català literari estàndard. Mantén el registre i ritme de l'original. "
        "Per a frases canòniques o cites cèlebres, usa la traducció catalana establerta si existeix "
        "(ex: Hamlet → Salvador Oliva). En poesia, respecta la mètrica i el ritme originals quan sigui possible. "
        "Si és un haiku (japonès), respecta estrictament la forma 5-7-5 síl·labes en català."
    ),
    "teatre": (
        "Tradueix al català literari estàndard. Mantén el registre i ritme de l'original. "
        "Per a frases canòniques o cites cèlebres, usa la traducció catalana establerta si existeix "
        "(ex: Hamlet → Salvador Oliva). En teatre, busca l'oralitat: ha de sonar bé en veu alta. "
        "Frases que es puguin dir, amb to viu i dinàmic."
    ),
    "narrativa": (
        "Tradueix al català literari estàndard. Mantén el registre i ritme de l'original. "
        "Per a frases canòniques o cites cèlebres, usa la traducció catalana establerta si existeix "
        "(ex: Hamlet → Salvador Oliva). En narrativa, preserva la VEU del narrador i els diàlegs naturals."
    ),
    "assaig": (
        "Tradueix al català literari estàndard. Mantén el registre i ritme de l'original. "
        "Per a frases canòniques o cites cèlebres, usa la traducció catalana establerta si existeix "
        "(ex: Hamlet → Salvador Oliva). En assaig, prioritza la claredat argumentativa i el to personal de l'autor."
    ),
    "oriental": (
        "Tradueix al català literari estàndard. Mantén el registre i ritme de l'original. "
        "Per a frases canòniques o cites cèlebres, usa la traducció catalana establerta si existeix "
        "(ex: Hamlet → Salvador Oliva). En textos orientals, busca l'equilibri entre fidelitat literal "
        "i llegibilitat. Si és POESIA ORIENTAL (haiku, tanka), respecta la mètrica original: "
        "5-7-5 síl·labes per haiku. Compta: vocals = 1 síl·laba, diftongs = 1 síl·laba."
    ),
}


def get_api_key() -> str | None:
    """Obté la clau API de Venice (env o fitxer de config)."""
    key = os.environ.get("VENICE_API_KEY", "").strip()
    if key:
        return key
    clawdbot_config = Path.home() / ".clawdbot" / "clawdbot.json"
    if clawdbot_config.exists():
        try:
            cfg = json.loads(clawdbot_config.read_text())
            for skill_name in ("venice-ai", "venice-ai-media"):
                k = (cfg.get("skills", {}).get("entries", {})
                     .get(skill_name, {}).get("env", {})
                     .get("VENICE_API_KEY", ""))
                if k:
                    return k.strip()
        except (json.JSONDecodeError, OSError):
            pass
    return None


def load_models_conf(project_dir: Path) -> dict:
    """Llegeix models.conf i retorna un dict de {group:subtype} → {model, timeout, thinking}."""
    conf_path = project_dir / "sistema" / "config" / "models.conf"
    result = {}
    if not conf_path.exists():
        return result
    with open(conf_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if not line or "=" not in line:
                continue
            key_part, val_part = line.split("=", 1)
            key_part = key_part.strip()
            val_part = val_part.strip()
            # Parse model name (first token)
            tokens = val_part.split()
            model = tokens[0]
            # Parse flags
            timeout_match = re.search(r'timeout=(\d+)', val_part)
            thinking_match = re.search(r'thinking=(on|off)', val_part, re.IGNORECASE)
            result[key_part] = {
                "model": model,
                "timeout": int(timeout_match.group(1)) if timeout_match else 300,
                "thinking": thinking_match.group(1).lower() if thinking_match else "off",
            }
    return result


def get_model_config(models_conf: dict, group: str, subtype: str) -> dict:
    """Busca configuració de model amb fallback a default."""
    key = f"{group}:{subtype}"
    if key in models_conf:
        return models_conf[key]
    if f"{group}:default" in models_conf:
        return models_conf[f"{group}:default"]
    return {"model": DEFAULT_MODEL, "timeout": 300, "thinking": "off"}


def parse_venice_response(stdout: str) -> tuple[str, str]:
    """
    Parseja la resposta de Venice CLI.
    - Extreu blocs <thinking>...</thinking> (regex DOTALL)
    - Retorna (text_net, thinking_raw)
    """
    thinking_raw = ""
    text = stdout

    # Extreure blocs <thinking>...</thinking> (tags estàndard)
    thinking_blocks = re.findall(r'<thinking>(.*?)</thinking>', text, flags=re.DOTALL)
    if thinking_blocks:
        thinking_raw = "\n".join(thinking_blocks)
        text = re.sub(r'<thinking>.*?</thinking>\s*', '', text, flags=re.DOTALL)

    # Extreure blocs Unicode ＜thinking＞...＜/thinking＞
    unicode_blocks = re.findall(r'＜thinking＞(.*?)＜/thinking＞', text, flags=re.DOTALL)
    if unicode_blocks:
        thinking_raw += ("\n" if thinking_raw else "") + "\n".join(unicode_blocks)
        text = re.sub(r'＜thinking＞.*?＜/thinking＞\s*', '', text, flags=re.DOTALL)

    # Netejar tags solts
    text = re.sub(r'^\s*[＜<]/?thinking[＞>]\s*$', '', text, flags=re.MULTILINE)
    text = text.strip()

    return text, thinking_raw


def run_venice_api(
    prompt: str,
    model: str,
    max_tokens: int = 4096,
    system_prompt: str = "",
    disable_thinking: bool = True,
    temperature: float = 0.3,
) -> tuple[str, dict]:
    """
    Crida l'API REST de Venice directament.
    Retorna (text_traduit, metadades).
    """
    key = get_api_key()
    if not key:
        raise RuntimeError("Venice API key no trobada")

    url = f"{API_BASE}/chat/completions"
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    venice_params = {}
    if disable_thinking:
        venice_params["disable_thinking"] = True
        venice_params["strip_thinking_response"] = True
    if venice_params:
        payload["venice_parameters"] = venice_params

    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, method="POST", headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
        "User-Agent": USER_AGENT,
    }, data=data)

    start_time = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=120)
        body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {err_body}")
    except Exception as e:
        raise RuntimeError(f"Error de connexió: {e}")
    latency_ms = int((time.time() - start_time) * 1000)

    choices = body.get("choices", [{}])
    if not choices:
        raise RuntimeError("Resposta sense choices")

    msg = choices[0].get("message", {})
    content = msg.get("content", "") or ""
    reasoning_content = msg.get("reasoning_content", "") or ""

    usage = body.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    total_tokens = usage.get("total_tokens", 0)
    # Venice pot incloure reasoning_tokens a completion_tokens_details
    ctd = usage.get("completion_tokens_details", {}) or {}
    reasoning_tokens = ctd.get("reasoning_tokens", 0) if isinstance(ctd, dict) else 0

    metadades = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "reasoning_tokens": reasoning_tokens,
        "total_tokens": total_tokens,
        "latency_ms": latency_ms,
        "model": model,
    }

    # Si content és buit però hi ha reasoning_content, usar reasoning com a fallback
    # (això passa amb Claude quan thinking està activat i no hi ha disable_thinking)
    if not content.strip() and reasoning_content.strip():
        content = reasoning_content.strip()
        metadades["used_reasoning_as_content"] = True

    return content.strip(), metadades


def run_venice(
    prompt: str,
    model: str,
    max_tokens: int = 4096,
    disable_thinking: bool = True,
    system_prompt: str = "",
    temperature: float = 0.3,
) -> tuple[str, dict]:
    """
    Wrapper que usa l'API REST directa.
    Si l'API falla amb 401, fallback al Venice CLI.
    """
    try:
        return run_venice_api(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            disable_thinking=disable_thinking,
            temperature=temperature,
        )
    except RuntimeError as e:
        err_text = str(e).lower()
        if "401" in err_text or "unauthorized" in err_text:
            # Fallback al Venice CLI (que llegeix la key del seu propi mecanisme)
            extra_args = ["--disable-thinking"] if disable_thinking else []
            cmd = [
                "python3", str(VENICE_SCRIPT),
                "chat",
                "--model", model,
                "--max-tokens", str(max_tokens),
                "--temperature", str(temperature),
                "--no-venice-system-prompt",
                "--timeout", "120",
            ] + extra_args

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=VENICE_TIMEOUT,
                input=prompt,
            )

            if result.returncode != 0:
                err_text = result.stdout.strip() if result.stdout.strip() else result.stderr.strip()
                raise RuntimeError(f"Venice CLI error: {err_text}")

            if not result.stdout.strip():
                raise RuntimeError("Venice va retornar resposta buida")

            content, thinking_raw = parse_venice_response(result.stdout)
            if not content:
                raise RuntimeError("Venice va retornar només thinking, sense contingut")

            metadades = {"used_cli_fallback": True, "thinking_raw_len": len(thinking_raw)}
            return content, metadades
        raise


def log_translation_metrics(
    metrics: dict,
    log_path: Path | None = None,
) -> None:
    """Escriu mètriques de traducció a un log JSONL."""
    if log_path is None:
        log_path = Path.home() / "biblioteca-universal-arion" / "sistema" / "logs" / "translation_metrics.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(metrics, ensure_ascii=False) + "\n")


def validate_length_ratio(input_text: str, output_text: str) -> tuple[bool, float]:
    """
    Valida que la longitud output estigui entre 0.6x i 1.8x de l'input.
    Retorna (is_valid, ratio).
    """
    input_len = len(input_text.strip())
    output_len = len(output_text.strip())
    if input_len == 0:
        return True, 0.0
    ratio = output_len / input_len
    return 0.6 <= ratio <= 1.8, ratio


def load_metadata(obra_dir: Path) -> dict:
    """Carrega metadata.yml."""
    meta_path = obra_dir / "metadata.yml"
    if not meta_path.exists():
        return {
            "titol": obra_dir.name.replace("-", " ").title(),
            "autor": obra_dir.parent.name.replace("-", " ").title(),
            "llengua": "llatí",
            "genere": "narrativa",
        }

    import yaml
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = yaml.safe_load(f) or {}

    obra = meta.get("obra", meta)
    return {
        "titol": obra.get("titol", obra.get("title", obra_dir.name)),
        "autor": obra.get("autor", obra.get("author", obra_dir.parent.name)),
        "llengua": obra.get("llengua_original", obra.get("source_language", "llatí")),
        "genere": obra.get("genere", obra.get("category", "narrativa")),
    }


def load_glossari(obra_dir: Path) -> str:
    """Carrega glossari.yml si existeix."""
    glossari_path = obra_dir / "glossari.yml"
    if not glossari_path.exists():
        return ""

    import yaml
    with open(glossari_path, "r", encoding="utf-8") as f:
        glossari = yaml.safe_load(f) or {}

    if not glossari:
        return ""

    termes = []
    for terme, traduccio in glossari.items():
        if isinstance(traduccio, dict):
            traduccio = traduccio.get("ca", traduccio.get("traduccio", ""))
        termes.append(f"  - {terme}: {traduccio}")

    return "\n".join(termes)


def load_memoria_contextual(obra_dir: Path) -> str:
    """Carrega la memòria contextual de la traducció anterior."""
    memoria_path = obra_dir / ".memoria_contextual.json"
    if not memoria_path.exists():
        return ""

    with open(memoria_path, "r", encoding="utf-8") as f:
        try:
            memoria = json.load(f)
            return memoria.get("ultim_context", "")
        except json.JSONDecodeError:
            return ""


def save_memoria_contextual(obra_dir: Path, context: str) -> None:
    """Guarda la memòria contextual per a la propera sessió."""
    memoria_path = obra_dir / ".memoria_contextual.json"
    memoria = {"ultim_context": context, "timestamp": time.time()}

    if memoria_path.exists():
        with open(memoria_path, "r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
                memoria["historial"] = existing.get("historial", [])
                memoria["historial"].append({"context": context, "timestamp": time.time()})
            except json.JSONDecodeError:
                pass

    with open(memoria_path, "w", encoding="utf-8") as f:
        json.dump(memoria, f, ensure_ascii=False, indent=2)


def chunk_text(text: str, max_chars: int = CHUNK_SIZE) -> list[str]:
    """Divideix el text en chunks respectant els paràgrafs."""
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 > max_chars and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = para
        else:
            current_chunk += "\n\n" + para if current_chunk else para

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def build_translation_prompt(
    text: str,
    titol: str,
    autor: str,
    llengua: str,
    genere: str,
    glossari: str = "",
    context_anterior: str = "",
) -> str:
    """Construeix el prompt per a la traducció amb system prompt reforçat."""

    genre_instructions = {
        "filosofia": "Traducció filosòfica: claredat expositiva, precisió terminològica, respecte per l'argumentació. To didàctic i rigorós.",
        "poesia": "Traducció poètica: sentit > ritme > literalitat. Busca equivalents sonors. Permet llicències per musicalitat.",
        "teatre": "Traducció teatral: oralitat. Ha de sonar bé en veu alta. Frases que 'es puguin dir'. To viu i dinàmic.",
        "narrativa": "Traducció narrativa: preserva la VEU del narrador. Diàlegs naturals i creïbles. Ritme narratiu fidel a l'original.",
        "assaig": "Traducció d'assaig: claredat argumentativa. To personal de l'autor. Transicions lògiques fluides.",
        "oriental": "Traducció oriental: equilibri entre fidelitat i llegibilitat. Respecta les convencions del gènere oriental.",
    }

    instruccions = genre_instructions.get(genere, genre_instructions["narrativa"])

    prompt_parts = [
        f"[TRADUCCIÓ AL CATALÀ]",
        f"",
        f"Obra: {titol}",
        f"Autor: {autor}",
        f"Llengua original: {llengua}",
        f"Gènere: {genere}",
        f"",
        f"## Instruccions de traducció",
        f"",
        f"{instruccions}",
        f"",
    ]

    if glossari:
        prompt_parts.extend([
            f"## Glossari terminològic",
            f"",
            f"{glossari}",
            f"",
        ])

    if context_anterior:
        prompt_parts.extend([
            f"## Context anterior (últims paràgrafs traduïts)",
            f"",
            f"{context_anterior}",
            f"",
        ])

    prompt_parts.extend([
        f"## Text original ({llengua})",
        f"",
        f"```{llengua}",
        f"{text}",
        f"```",
        f"",
        f"## Traducció al català",
        f"",
        f"Tradueix el text anterior al català seguint les instruccions. Només retorna la traducció, sense comentaris addicionals.",
    ])

    return "\n".join(prompt_parts)


def translate_chunk(
    chunk: str,
    metadata: dict,
    glossari: str,
    context_anterior: str,
    model: str,
    disable_thinking: bool,
    recursion_depth: int = 0,
    max_depth: int = 3,
) -> tuple[str, dict]:
    """
    Tradueix un chunk amb Venice.
    Suporta divisió recursiva controlada i retry amb thinking toggled.
    Retorna (text_traduit, metadades).
    """
    if recursion_depth >= max_depth:
        raise RuntimeError(
            f"Màxima profunditat de recursió assolida ({max_depth}) "
            f"per chunk de {len(chunk)} chars"
        )

    prompt = build_translation_prompt(
        text=chunk,
        titol=metadata["titol"],
        autor=metadata["autor"],
        llengua=metadata["llengua"],
        genere=metadata["genere"],
        glossari=glossari,
        context_anterior=context_anterior,
    )

    system_prompt = SYSTEM_PROMPTS.get(metadata.get("genere", "narrativa"), SYSTEM_PROMPTS["narrativa"])

    all_metrics = {
        "model": model,
        "task": metadata.get("genere", "unknown"),
        "input_chars": len(chunk),
        "retries": 0,
        "prompt_preview": prompt[:200],
    }

    for attempt in range(MAX_RETRIES):
        try:
            result, meta = run_venice(
                prompt=prompt,
                model=model,
                max_tokens=4096,
                disable_thinking=disable_thinking,
                system_prompt=system_prompt,
                temperature=0.3,
            )

            all_metrics["tokens_in"] = meta.get("prompt_tokens", 0)
            all_metrics["tokens_thinking"] = meta.get("reasoning_tokens", 0)
            all_metrics["tokens_output"] = meta.get("completion_tokens", 0)
            all_metrics["latency_ms"] = meta.get("latency_ms", 0)
            all_metrics["used_api"] = not meta.get("used_cli_fallback", False)

            # Validació de ratio longitud
            is_valid, ratio = validate_length_ratio(chunk, result)
            all_metrics["ratio_longitud"] = round(ratio, 3)

            if not is_valid and attempt < MAX_RETRIES - 1:
                print(f"⚠️ Ratio invàlid ({ratio:.2f}), reintentant amb temperatura ajustada...")
                all_metrics["retries"] += 1
                # Retry amb temperatura lleugerament diferent
                retry_result, retry_meta = run_venice(
                    prompt=prompt,
                    model=model,
                    max_tokens=4096,
                    disable_thinking=disable_thinking,
                    system_prompt=system_prompt,
                    temperature=0.2,
                )
                is_valid_retry, ratio_retry = validate_length_ratio(chunk, retry_result)
                all_metrics["ratio_longitud"] = round(ratio_retry, 3)
                all_metrics["tokens_in"] = retry_meta.get("prompt_tokens", all_metrics["tokens_in"])
                all_metrics["tokens_thinking"] = retry_meta.get("reasoning_tokens", all_metrics["tokens_thinking"])
                all_metrics["tokens_output"] = retry_meta.get("completion_tokens", all_metrics["tokens_output"])
                all_metrics["latency_ms"] = retry_meta.get("latency_ms", all_metrics["latency_ms"])
                all_metrics["retries"] += 1

                if is_valid_retry:
                    result = retry_result
                else:
                    # Acceptar de totes maneres si el ratio no és catastròfic
                    if ratio_retry < 0.3 or ratio_retry > 3.0:
                        raise RuntimeError(f"Traducció invàlida: ratio={ratio_retry:.2f} (fora de rang)")
                    print(f"⚠️ Ratio encara invàlid ({ratio_retry:.2f}), però acceptable. Continuant.")
                    result = retry_result

            # Log de mètriques
            log_translation_metrics(all_metrics)
            return result, all_metrics

        except subprocess.TimeoutExpired:
            if len(chunk) > 500 and recursion_depth < max_depth:
                print(f"⏱️ Timeout ({VENICE_TIMEOUT}s), dividint chunk de {len(chunk)} chars "
                      f"(nivell {recursion_depth+1}/{max_depth})...")
                half = len(chunk) // 2
                first_half, _ = translate_chunk(
                    chunk[:half], metadata, glossari, context_anterior, model,
                    disable_thinking, recursion_depth=recursion_depth + 1, max_depth=max_depth
                )
                second_half, _ = translate_chunk(
                    chunk[half:], metadata, glossari, first_half[-500:], model,
                    disable_thinking, recursion_depth=recursion_depth + 1, max_depth=max_depth
                )
                return first_half + "\n\n" + second_half, all_metrics
            else:
                raise RuntimeError(
                    f"Timeout en chunk petit ({len(chunk)} chars) "
                    f"després de {VENICE_TIMEOUT}s"
                )
        except RuntimeError as e:
            err_msg = str(e).lower()
            if "rate limit" in err_msg:
                print(f"Rate limit, esperant 30s...")
                time.sleep(30)
            elif "timeout silenciós" in err_msg or "empty" in err_msg or "buida" in err_msg:
                # Resposta buida: retry amb disable_thinking forçat
                if attempt < MAX_RETRIES - 1:
                    print(f"⚠️ Resposta buida, reintentant amb disable_thinking=True...")
                    disable_thinking = True
                    time.sleep(5)
                else:
                    raise
            elif attempt < MAX_RETRIES - 1:
                print(f"Error (intento {attempt+1}/{MAX_RETRIES}): {e}")
                time.sleep(10)
            else:
                raise

    raise RuntimeError(f"Max retries exhaurits per chunk de {len(chunk)} chars")


def main():
    parser = argparse.ArgumentParser(description="Traducció amb Venice AI")
    parser.add_argument("--autor", help="Nom de l'autor (ex: aristotil)")
    parser.add_argument("--obra", help="Nom de l'obra (ex: peri-psykhes)")
    parser.add_argument("--ruta", help="Ruta directa a l'obra (ex: obres/filosofia/aristotil/peri-psykhes)")
    parser.add_argument("--model", help="Model a utilitzar (ex: claude-opus-4-7)")
    parser.add_argument("--start", type=int, default=0, help="Chunk d'inici (per reprendre)")
    parser.add_argument("--continuar", action="store_true", help="Continuar des de l'últim chunk")
    args = parser.parse_args()

    # Determinar ruta de l'obra
    if args.ruta:
        obra_dir = Path(args.ruta).resolve()
    elif args.autor and args.obra:
        for categoria in ["filosofia", "narrativa", "poesia", "teatre", "assaig", "oriental"]:
            candidate = Path(f"obres/{categoria}/{args.autor}/{args.obra}")
            if candidate.exists():
                obra_dir = candidate.resolve()
                break
        else:
            print(f"❌ No s'ha trobat l'obra: {args.autor}/{args.obra}")
            sys.exit(1)
    else:
        print("❌ Cal especificar --autor i --obra o --ruta")
        sys.exit(1)

    if not obra_dir.exists():
        print(f"❌ No existeix: {obra_dir}")
        sys.exit(1)

    # Carregar metadata
    metadata = load_metadata(obra_dir)
    print(f"📖 {metadata['titol']} de {metadata['autor']}")
    print(f"🌐 {metadata['llengua']} → català | Gènere: {metadata['genere']}")

    # Carregar models.conf
    project_dir = obra_dir
    while project_dir.name != "biblioteca-universal-arion" and project_dir.parent != project_dir:
        project_dir = project_dir.parent
    if not (project_dir / "sistema" / "config" / "models.conf").exists():
        project_dir = obra_dir
        while project_dir.parent != project_dir:
            if (project_dir / "sistema" / "config" / "models.conf").exists():
                break
            project_dir = project_dir.parent
    models_conf = load_models_conf(project_dir)

    # Seleccionar model i configuració
    if args.model:
        model = MODEL_ALIASES.get(args.model, args.model)
        # Sempre llegir thinking de models.conf, fins i tot quan se sobreescriu el model
        model_config = get_model_config(models_conf, "translate", metadata["genere"])
        model_config["model"] = model  # Sobreescriure model però mantenir thinking de conf
    else:
        genre = metadata["genere"]
        model_config = get_model_config(models_conf, "translate", genre)
        if not model_config or not model_config.get("model"):
            model_config = {"model": GENRE_MODELS.get(genre, DEFAULT_MODEL), "timeout": 300, "thinking": "off"}
        model = model_config["model"]

    disable_thinking = model_config.get("thinking", "off").lower() != "on"
    print(f"🤖 Model: {model} (thinking={'off' if disable_thinking else 'on'})")

    # Carregar original
    original_path = obra_dir / "original.md"
    if not original_path.exists():
        print(f"❌ No existeix original.md")
        sys.exit(1)

    with open(original_path, "r", encoding="utf-8") as f:
        text_original = f.read()

    # Netejar metadata del font
    for footer in ["*Text de domini públic", "*Traducció de domini públic"]:
        if footer in text_original:
            text_original = text_original.split(footer)[0].strip()

    # Trobar inici del contingut
    match = re.search(r'^(##\s+|[一二三四五六七八九十]+\s*$|[IVXLCDM]+\s*$)', text_original, re.MULTILINE)
    if match:
        text_narratiu = text_original[match.start():]
    else:
        text_narratiu = text_original

    # Treure footer final
    footer_hrule = '---\n\n*'
    last_pos = text_narratiu.rfind(footer_hrule)
    if last_pos > 0 and (len(text_narratiu) - last_pos) < 200:
        text_narratiu = text_narratiu[:last_pos].strip()

    print(f"📝 Text: {len(text_narratiu)} caràcters")

    # Dividir en chunks
    chunks = chunk_text(text_narratiu)
    print(f"📦 Chunks: {len(chunks)}")

    # Carregar glossari
    glossari = load_glossari(obra_dir)

    # === ESCRIPTURA INCREMENTAL ===
    # Cada chunk exitós s'afegeix immediatament a traduccio.md.
    # Si el procés mor, --continuar reprèn des de l'últim chunk completat.

    traduccio_path = obra_dir / "traduccio.md"

    def count_completed_chunks(path: Path) -> int:
        """Compta quants chunks ja estan traduïts al traduccio.md."""
        if not path.exists():
            return 0
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        # Els chunks estan separats per \n\n dins la secció de body
        # Format: header\n---\n\nbody\n---\n\nfooter
        # Extreure el body (entre el primer --- i l'últim ---)
        parts = content.split("\n---\n")
        if len(parts) < 3:
            return 0  # No hi ha body encara
        body = "---\n".join(parts[1:-1]).strip()
        if not body:
            return 0
        # Cada chunk traduït és un bloc separador per \n\n
        blocks = [b.strip() for b in body.split("\n\n") if b.strip()]
        return len(blocks)

    def write_header(path: Path, metadata: dict) -> None:
        """Escriu la capçalera inicial si no existeix."""
        header = f"""# {metadata['titol']}
*{metadata['autor']}*

Traduït del {metadata['llengua']} per Biblioteca Arion

---

"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(header)

    def append_chunk(path: Path, text: str) -> None:
        """Afegeix un chunk de manera atòmica via fitxer temporal."""
        tmp = path.parent / ".chunk_pending.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("\n\n" + text)
        # Atomic: read existing + append
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n\n" + text)
        tmp.unlink(missing_ok=True)

    def write_footer(path: Path) -> None:
        """Afegeix el peu de pàgina final."""
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n\n---\n\n*Traducció de domini públic.*\n")

    def clean_footer_for_continue(path: Path) -> None:
        """Treu el footer si existeix (per poder continuar afegint chunks)."""
        if not path.exists():
            return  # No hi ha traduccio.md encara: res a netejar (--continuar des de zero)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if "*Traducció de domini públic*" in content:
            content = content.split("\n---\n\n*Traducció de domini públic*")[0].strip()
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

    # Determinar start_chunk
    start_chunk = args.start
    if args.continuar:
        start_chunk = count_completed_chunks(traduccio_path)
        # Netejar footer per poder afegir
        clean_footer_for_continue(traduccio_path)
        # Assegurar que el fitxer existeix amb header
        if not traduccio_path.exists():
            write_header(traduccio_path, metadata)
        print(f"↩️ Continuant des del chunk {start_chunk} ({count_completed_chunks(traduccio_path)} blocs al fitxer)")
    else:
        # Traducció nova: escriure header
        write_header(traduccio_path, metadata)

    # Context anterior
    context_anterior = ""
    if traduccio_path.exists():
        with open(traduccio_path, "r", encoding="utf-8") as f:
            existing = f.read()
        context_anterior = existing[-500:] if len(existing) > 500 else existing
    context_anterior = load_memoria_contextual(obra_dir) or context_anterior

    # Traduir chunks amb escriptura incremental
    errors = []
    total_metrics = []
    MAX_CHUNK_RETRIES = 3
    chunks_written = 0

    for i, chunk in enumerate(chunks[start_chunk:], start=start_chunk):
        print(f"\n[{i+1}/{len(chunks)}] Traduint {len(chunk)} caràcters...")

        traduccio = None
        last_error = None

        for attempt in range(1, MAX_CHUNK_RETRIES + 1):
            try:
                traduccio, metrics = translate_chunk(
                    chunk=chunk,
                    metadata=metadata,
                    glossari=glossari,
                    context_anterior=context_anterior,
                    model=model,
                    disable_thinking=disable_thinking,
                )
                total_metrics.append(metrics)
                print(f"✅ Chunk {i+1} completat (ratio={metrics.get('ratio_longitud', 'N/A')}, "
                      f"tokens={metrics.get('tokens_output', 'N/A')})")
                break
            except Exception as e:
                last_error = str(e)
                print(f"⚠️ Intent {attempt}/{MAX_CHUNK_RETRIES} fallat per chunk {i+1}: {e}")
                if attempt < MAX_CHUNK_RETRIES:
                    time.sleep(5 * attempt)  # Backoff: 5s, 10s

        if traduccio is None:
            print(f"❌ Chunk {i+1} fallat després de {MAX_CHUNK_RETRIES} intents: {last_error}")
            errors.append((i, last_error))
            continue  # Saltar aquest chunk, no escriure res

        # Actualitzar context i memòria
        context_anterior = traduccio[-500:] if len(traduccio) > 500 else traduccio
        save_memoria_contextual(obra_dir, context_anterior)

        # ESCRIURE INCREMENTALMENT
        append_chunk(traduccio_path, traduccio)
        chunks_written += 1
        print(f"💾 Chunk {i+1} escrit a disc ({chunks_written} nous aquesta sessió)")

    # Escriure footer final
    write_footer(traduccio_path)
    print(f"\n✅ Traducció guardada a: {traduccio_path}")

    # Guardar memòria final
    save_memoria_contextual(obra_dir, context_anterior)

    # Eliminar .needs_fix o .fixing
    for f in [".needs_fix", ".fixing"]:
        p = obra_dir / f
        if p.exists():
            p.unlink()
            print(f"🗑️ Eliminat {f}")

    # Report d'errors
    if errors:
        print(f"\n⚠️ Errors en {len(errors)} chunks:")
        for idx, err in errors:
            print(f"   Chunk {idx}: {err}")

    print(f"\n📊 Estadístiques:")
    print(f"   Chunks escrits: {chunks_written}")
    print(f"   Errors: {len(errors)}")
    print(f"   Model utilitzat: {model}")
    if total_metrics:
        total_tokens = sum(m.get("tokens_output", 0) for m in total_metrics)
        avg_ratio = sum(m.get("ratio_longitud", 0) for m in total_metrics) / len(total_metrics)
        total_retries = sum(m.get("retries", 0) for m in total_metrics)
        print(f"   Tokens totals: {total_tokens}")
        print(f"   Ratio mitjà: {avg_ratio:.2f}")
        print(f"   Retries: {total_retries}")


if __name__ == "__main__":
    main()
