import re
from typing import List
from .base import DetectorPlugin, CalcDetectat, TipusCalc

class DetectorLlati(DetectorPlugin):
    @property
    def llengua(self) -> str:
        return "llatí"
        
    def detectar(self, text: str) -> List[CalcDetectat]:
        calcs = []
        partitiu = re.finditer(r'\b(molts|alguns|pocs|cap)\s+dels?\s+\w+', text, re.IGNORECASE)
        for match in partitiu:
            calcs.append(CalcDetectat(
                tipus="calc_sintactic",
                text_original=match.group(),
                posicio=(match.start(), match.end()),
                explicacio="Possible genitiu partitiu llatí",
                suggeriment="Considerar eliminar 'dels/de les' si no és necessari",
                severitat=3.0,
                llengua_origen=self.llengua,
            ))
        return calcs
