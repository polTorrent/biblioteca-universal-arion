from __future__ import annotations

import re

from .base import CalcDetectat, DetectorPlugin


class DetectorAlemany(DetectorPlugin):
    @property
    def llengua(self) -> str:
        return "alemany"

    def detectar(self, text: str) -> list[CalcDetectat]:
        resultats: list[CalcDetectat] = []
        falsos_amics = {
            r"\bbekommen\b": ("rebre", "Fals amic: 'bekommen' significa 'rebre', no pas 'convertir-se' o 'arribar a ser'."),
            r"\bgymnasium\b": ("institut", "Fals amic: 'Gymnasium' (alemany) és l'institut, no un espai per fer esport."),
            r"\bsympathisch\b": ("agradable", "Fals amic: 'sympathisch' es refereix a algú simpàtic o agradable, no pas compassiu."),
            r"\brat\b": ("consell", "Fals amic: 'Rat' significa 'consell', no el rosegador."),
        }

        for patro, (suggeriment, explicacio) in falsos_amics.items():
            for regex_match in re.finditer(patro, text, flags=re.IGNORECASE):
                inici, fi = regex_match.span()
                resultats.append(CalcDetectat(
                    tipus="fals_amic",
                    text_original=text[inici:fi],
                    posicio=(inici, fi),
                    explicacio=explicacio,
                    suggeriment=suggeriment,
                    severitat=6.0,
                    llengua_origen="de",
                ))
        return resultats
