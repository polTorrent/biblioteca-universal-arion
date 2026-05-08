#!/usr/bin/env python3
"""Extreu la Cena Trimalchionis (cap. XXVI-LXXVIII) del Satyricon complet."""
import sys
from pathlib import Path


def main() -> None:
    obra_dir = Path("obres/narrativa/petroni/cena-trimalchionis-el-banquet-de-trimalcio")
    original = obra_dir / "original.md"

    if not original.exists():
        print(f"ERROR: no existeix {original}")
        sys.exit(1)

    lines: list[str] = original.read_text(encoding="utf-8").splitlines(keepends=True)

    # Cena Trimalchionis: cap XXVI fins final cap LXXVIII
    start_idx: int | None = None
    end_idx: int | None = None
    for i, line in enumerate(lines):
        if line.strip() == "## XXVI.":
            start_idx = i
        if line.strip() == "## LXXIX.":
            end_idx = i
            break

    if start_idx is None or end_idx is None:
        print(f"ERROR: start={start_idx}, end={end_idx}")
        sys.exit(1)

    cena_lines = lines[start_idx:end_idx]
    cena_text = "".join(cena_lines).strip()
    print(f"Extracted lines {start_idx + 1}-{end_idx} ({len(cena_lines)} lines, {len(cena_text)} chars)")

    header = """**Autor:** Petronius
**Font:** [wikisource](https://la.wikisource.org/wiki/Satyricon)
**Llengua:** llatí

---

"""

    original.write_text(header + cena_text + "\n", encoding="utf-8")
    print("original.md reescrit amb la Cena Trimalchionis (cap. XXVI-LXXVIII)")


if __name__ == "__main__":
    main()
