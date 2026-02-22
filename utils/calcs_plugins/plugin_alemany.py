from typing import List
import re
from .base import DetectorPlugin, CalcDetectat, TipusCalc

class DetectorAlemany(DetectorPlugin):
    @property
    def llengua(self) -> str:
        return "alemany"

    def detectar(self, text: str) -> List[CalcDetectat]:
        resultats = []
        falsos_amics = {
            r"\bbekommen\b": ("rebre", "Fals amic: 'bekommen' significa 'rebre', no pas 'convertir-se' o 'arribar a ser'."),
            r"\bgymnasium\b": ("institut", "Fals amic: 'Gymnasium' (alemany) és l'institut, no un espai per fer esport."),
            r"\bsympathisch\b": ("agradable", "Fals amic: 'sympathisch' es refereix a algú simpàtic o agradable, no pas compassiu."),
            r"\brat\b": ("consell", "Fals amic: 'Rat' significa 'consell', no el rosegador."),
        }
        
        for patro, (suggeriment, explicacio) in falsos_amics.items():
            for regex_match in re.finditer(patro, text.lower()):
                inici, fi = regex_match.span()
                original = text[inici:fi]
                resultats.append(CalcDetectat(
                    tipus="fals_amic",
                    text_original=original,
                    posicio=(inici, fi),
                    explicacio=explicacio,
                    suggeriment=suggeriment,
                    severitat=6.0,
                    llengua_origen="de"
                ))
        return resultats
