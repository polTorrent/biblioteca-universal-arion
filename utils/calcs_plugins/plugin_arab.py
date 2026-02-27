from __future__ import annotations

import re

from .base import CalcDetectat, DetectorPlugin

# Cadena genitiva: 3+ sintagmes encadenats amb "de/del/de la/de l'/dels/de les"
_IDAFA_RE = re.compile(
    r"\b(\w+(?:\s+\w+)?)"  # primer sintagma
    r"(?:\s+(?:del?|de\s+(?:la|l['']\w+|les|els))\s+\w+(?:\s+\w+)?){2,}",  # 2+ genitius
    re.IGNORECASE,
)


class DetectorArab(DetectorPlugin):
    @property
    def llengua(self) -> str:
        return "àrab"

    def detectar(self, text: str) -> list[CalcDetectat]:
        calcs: list[CalcDetectat] = []

        sense_copula = re.finditer(
            r"\b(El|La|Els|Les|Un|Una)\s+\w+\s+(molt\s+)?"
            r"(gran|petit|bo|dolent|bell|lleig|nou|vell|alt|baix|ric|pobre)\b",
            text,
        )
        for match in sense_copula:
            fragment = match.group()
            if " és " not in fragment and " són " not in fragment and " era " not in fragment:
                calcs.append(CalcDetectat(
                    tipus="calc_sintactic",
                    text_original=fragment,
                    posicio=(match.start(), match.end()),
                    explicacio="Possible frase nominal sense còpula (calc de l'àrab)",
                    suggeriment="Afegir verb 'ser'",
                    severitat=4.0,
                    llengua_origen=self.llengua,
                ))

        vso = re.finditer(
            r"\b(Va|Anà|Digué|Féu|Vingué|Sortí|Entrà)\s+(el|la|l['']\w+)\s+\w+",
            text,
        )
        for match in vso:
            calcs.append(CalcDetectat(
                tipus="calc_sintactic",
                text_original=match.group(),
                posicio=(match.start(), match.end()),
                explicacio="Ordre VSO (calc de l'àrab)",
                suggeriment="Considerar ordre SVO",
                severitat=4.0,
                llengua_origen=self.llengua,
            ))

        for match in _IDAFA_RE.finditer(text):
            calcs.append(CalcDetectat(
                tipus="calc_sintactic",
                text_original=match.group(),
                posicio=(match.start(), match.end()),
                explicacio="Possible cadena d'estat constructe (idafa)",
                suggeriment="Simplificar la cadena genitiva",
                severitat=4.0,
                llengua_origen=self.llengua,
            ))

        return calcs
