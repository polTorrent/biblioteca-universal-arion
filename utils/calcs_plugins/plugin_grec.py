import re
from typing import List
from .base import DetectorPlugin, CalcDetectat, TipusCalc

class DetectorGrec(DetectorPlugin):
    @property
    def llengua(self) -> str:
        return "grec"
        
    def detectar(self, text: str) -> List[CalcDetectat]:
        calcs = []
        men_de = re.search(r'per una banda.{5,50}per l\'altra', text, re.IGNORECASE)
        if men_de:
            calcs.append(CalcDetectat(
                tipus="calc_sintactic",
                text_original=men_de.group(),
                posicio=(men_de.start(), men_de.end()),
                explicacio="Possible calc de μέν...δέ grec",
                suggeriment="Valorar si l'estructura és necessària o simplificar",
                severitat=4.0,
                llengua_origen=self.llengua,
            ))
        return calcs
