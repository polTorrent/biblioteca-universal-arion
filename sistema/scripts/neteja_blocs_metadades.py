#!/usr/bin/env python3
"""Neteja dels blocs de metadades (JSON del refinador) filtrats a les obres.

Què fa
------
1. `.chunks_traduïts.json` de cada obra:
   - Si el contingut d'un chunk és només metadades o duu marques d'error, la clau
     s'elimina: el chunk es tornarà a traduir en la propera execució.
   - Si el contingut duu un bloc filtrat però se n'ha pogut recuperar el text
     traduït (p. ex. un JSON amb camp «traduccio» envoltat de tanques), es
     substitueix pel text net.
   - Si el contingut és correcte, no es toca.
2. Traduccions publicades (`traduccio*.md`): **només s'informa**, no es reescriuen
   (cal retraduir o corregir-les a mà).

Ús:
    python3 sistema/scripts/neteja_blocs_metadades.py            # simulació
    python3 sistema/scripts/neteja_blocs_metadades.py --aplica    # aplica canvis
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

_ARREL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ARREL / "sistema"))
sys.path.insert(0, str(_ARREL / "sistema" / "traduccio"))
sys.path.insert(0, str(_ARREL))

from agents.v2.sanititzacio import (  # noqa: E402
    netejar_i_validar,
    sembla_metadades,
    te_bloc_metadades,
)

OBRES = _ARREL / "obres"
REPORT = _ARREL / "reports"


def netejar_chunks(aplica: bool) -> dict:
    """Neteja els fitxers de chunks. Retorna el resum per informe."""
    resum = {"fitxers": 0, "chunks": 0, "recuperats": 0, "descartats": 0, "intactes": 0, "detalls": []}

    for path in sorted(OBRES.glob("**/.chunks_traduïts.json")):
        try:
            dades = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            resum["detalls"].append(f"⚠️  {path}: no s'ha pogut llegir ({e})")
            continue

        canvis = False
        obra = path.parent.relative_to(OBRES)
        for cid, valor in list(dades.items()):
            if not isinstance(valor, str):
                continue
            resum["chunks"] += 1
            net, motiu = netejar_i_validar(valor)
            if motiu is None and net == valor:
                resum["intactes"] += 1
                continue
            if motiu is None:
                dades[cid] = net
                canvis = True
                resum["recuperats"] += 1
                resum["detalls"].append(
                    f"♻️  {obra} {cid}: text net recuperat ({len(valor)} → {len(net)} caràcters)"
                )
            else:
                del dades[cid]
                canvis = True
                resum["descartats"] += 1
                resum["detalls"].append(
                    f"🗑️  {obra} {cid}: contingut descartat ({motiu}) → es retraduirà"
                )

        if canvis:
            resum["fitxers"] += 1
            if aplica:
                path.write_text(
                    json.dumps(dades, indent=2, ensure_ascii=False), encoding="utf-8"
                )
    return resum


def informar_traduccions() -> list[str]:
    """Detecta traduccions publicades amb blocs filtrats o marques d'error."""
    trobades = []
    for path in sorted(OBRES.glob("**/traduccio*.md")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        marques = text.count("[ERROR:")
        if te_bloc_metadades(text) or sembla_metadades(text) or marques:
            detall = []
            if te_bloc_metadades(text) or sembla_metadades(text):
                detall.append("bloc de metadades filtrat")
            if marques:
                detall.append(f"{marques} marques [ERROR:]")
            trobades.append(f"{path.relative_to(OBRES)} ({', '.join(detall)})")
    return trobades


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aplica", action="store_true", help="aplica els canvis (per defecte: simulació)")
    args = parser.parse_args()

    resum = netejar_chunks(args.aplica)
    traduccions = informar_traduccions()

    linies = [
        "# Neteja de blocs de metadades filtrats",
        f"Data: {datetime.now().isoformat(timespec='seconds')}",
        f"Mode: {'APLICAT' if args.aplica else 'SIMULACIÓ'}",
        "",
        "## Chunks",
        f"- Fitxers de chunks al disc: {len(list(OBRES.glob('**/.chunks_traduïts.json')))}",
        f"- Chunks revisats: {resum['chunks']}",
        f"- Correctes: {resum['intactes']}",
        f"- Text recuperat (bloc filtrat netejat): {resum['recuperats']}",
        f"- Descartats (es retraduiran): {resum['descartats']}",
        f"- Fitxers modificats: {resum['fitxers']}",
        "",
        "### Detall",
    ]
    linies.extend(f"- {d}" for d in resum["detalls"][:200])
    linies.append("")
    linies.append("## Traduccions publicades amb filtrat (cal corregir o retraduir)")
    if traduccions:
        linies.extend(f"- {t}" for t in traduccions)
    else:
        linies.append("- Cap")
    informe = "\n".join(linies)

    print(informe)
    REPORT.mkdir(exist_ok=True)
    desti = REPORT / f"neteja-blocs-metadades-{datetime.now().strftime('%Y-%m-%d')}.md"
    desti.write_text(informe + "\n", encoding="utf-8")
    print(f"\n[Informe desat a {desti.relative_to(_ARREL)}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
