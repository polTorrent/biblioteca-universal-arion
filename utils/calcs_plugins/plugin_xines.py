import re
from typing import List
from .base import DetectorPlugin, CalcDetectat

class DetectorXines(DetectorPlugin):
    @property
    def llengua(self) -> str:
        return "xinès"
        
    def detectar(self, text: str) -> List[CalcDetectat]:
        calcs = []
        classificadors = re.finditer(r'\b(un cap de|una boca de|un ull de|una mà de|un tros de persona)\b', text, re.IGNORECASE)
        for match in classificadors:
            calcs.append(CalcDetectat(tipus="calc_sintactic", text_original=match.group(), posicio=(match.start(), match.end()), explicacio="Classificador xinès traduït literalment", suggeriment="Adaptar a forma natural", severitat=5.0, llengua_origen=self.llengua))
            
        tema_comentari = re.finditer(r'\b(Aquesta cosa|Aquest assumpte|Aquell tema),\s*jo\s+', text)
        for match in tema_comentari:
            calcs.append(CalcDetectat(tipus="calc_sintactic", text_original=match.group(), posicio=(match.start(), match.end()), explicacio="Estructura tema-comentari", suggeriment="Reformular", severitat=4.0, llengua_origen=self.llengua))
            
        repeticio = re.finditer(r'\b(molt molt|ben bé|poc poc)\b', text, re.IGNORECASE)
        for match in repeticio:
            calcs.append(CalcDetectat(tipus="calc_sintactic", text_original=match.group(), posicio=(match.start(), match.end()), explicacio="Repetició per èmfasi", suggeriment="Usar superlatius", severitat=3.0, llengua_origen=self.llengua))
            
        return calcs
