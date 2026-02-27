from __future__ import annotations

import re
from .base import DetectorPlugin, CalcDetectat


class DetectorRus(DetectorPlugin):
    @property
    def llengua(self) -> str:
        return "rus"

    def detectar(self, text: str) -> list[CalcDetectat]:
        if not text:
            return []

        calcs: list[CalcDetectat] = []

        # Article absent (el rus no té articles; els traductors sovint els ometen)
        sense_article = re.finditer(
            r'\b(Home|Dona|Nen|Nena|Noia|Noi|Gat|Gos|Llibre|Taula|Cadira|Cotxe|Casa)'
            r'\s+(va|és|té|fa|estava|anava|tenia|feia|vol|pot|ha)\b',
            text,
        )
        for match in sense_article:
            calcs.append(CalcDetectat(
                tipus="article_absent",
                text_original=match.group(),
                posicio=(match.start(), match.end()),
                explicacio="Possible falta d'article (calc del rus)",
                suggeriment="Afegir article definit o indefinit",
                severitat=5.0,
                llengua_origen=self.llengua,
            ))

        # Doble negació
        doble_neg = re.finditer(
            r'\b(ningú|res|mai|cap|enlloc)\s+no\b', text, re.IGNORECASE,
        )
        for match in doble_neg:
            calcs.append(CalcDetectat(
                tipus="negacio_doble",
                text_original=match.group(),
                posicio=(match.start(), match.end()),
                explicacio="Doble negació",
                suggeriment="Verificar si la doble negació és natural aquí",
                severitat=3.0,
                llengua_origen=self.llengua,
            ))

        # Diminutius excessius (sufixos catalans, span limitat a 80 chars)
        diminutius = re.finditer(
            r'\b\w+(et|eta|ó|ona|í|ina|ell|ella)\b'
            r'.{1,80}'
            r'\b\w+(et|eta|ó|ona|í|ina|ell|ella)\b',
            text,
            re.IGNORECASE,
        )
        for match in diminutius:
            calcs.append(CalcDetectat(
                tipus="calc_sintactic",
                text_original=match.group(),
                posicio=(match.start(), match.end()),
                explicacio="Possible excés de diminutius (calc del rus)",
                suggeriment="Reduir l'ús de diminutius",
                severitat=3.0,
                llengua_origen=self.llengua,
            ))

        return calcs
