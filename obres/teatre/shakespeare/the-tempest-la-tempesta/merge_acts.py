#!/usr/bin/env python3
"""Fusiona els 5 actes traduïts en traduccio.md"""
import pathlib

base = pathlib.Path(__file__).parent
header = (
    "# La Tempesta\n\n"
    "## William Shakespeare\n\n"
    "Traducci\u00f3 al catal\u00e0 de *The Tempest* (c. 1610-1611)\n\n"
    "---\n\n"
    "### DRAMATIS PERSONAE\n\n"
    "- **ALONSO**, Rei de N\u00e0pols.\n"
    "- **SEBASTI\u00c0**, germ\u00e0 seu.\n"
    "- **PR\u00d2SPER**, leg\u00edtim Duc de Mil\u00e0.\n"
    "- **ANTONI**, germ\u00e0 seu, Duc usurpador de Mil\u00e0.\n"
    "- **FERRAN**, fill del Rei de N\u00e0pols.\n"
    "- **GONZALO**, conseller vell i honrat.\n"
    "- **ADRI\u00c0**, senyor.\n"
    "- **FRANCESC**, senyor.\n"
    "- **CALIBAN**, esclau salvatge i deforme.\n"
    "- **TR\u00cdNCULO**, buf\u00f3.\n"
    "- **ST\u00c8FANO**, majordom borratxo.\n"
    "- **Capit\u00e0** d'un vaixell.\n"
    "- **Contramaestre**.\n"
    "- **Mariners**.\n"
    "- **MIRANDA**, filla de Pr\u00f2sper.\n"
    "- **ARIEL**, esperit de l'aire.\n"
    "- **IRIS**, representada per esperits.\n"
    "- **CERES**, representada per esperits.\n"
    "- **JUNO**, representada per esperits.\n"
    "- **Nimfes**, representades per esperits.\n"
    "- **Segadors**, representats per esperits.\n"
    "- Altres esperits al servei de Pr\u00f2sper.\n\n"
    "ESCENA: _Un vaixell a alta mar; una illa deshabitada._\n\n"
    "---\n\n"
)

parts = [header]
for name in ["I", "II", "III", "IV", "V"]:
    f = base / f"acte_{name}_cat.md"
    parts.append(f.read_text())
    parts.append("\n\n---\n\n")

(base / "traduccio.md").write_text("".join(parts))
n_lines = "".join(parts).count("\n")
print(f"traduccio.md creat: {n_lines} l\u00ednies")
