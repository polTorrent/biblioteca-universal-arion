import re
from typing import List
from .base import DetectorPlugin, CalcDetectat

class DetectorRus(DetectorPlugin):
    @property
    def llengua(self) -> str:
        return "rus"
        
    def detectar(self, text: str) -> List[CalcDetectat]:
        calcs = []
        
        # Article absent
        sense_article = re.finditer(r'\b(Home|Dona|Nen|Nena|Noia|Noi|Gat|Gos|Llibre|Taula|Cadira|Cotxe|Casa)\s+(va|és|té|fa|estava|anava|tenia|feia|vol|pot|ha)\b', text)
        for match in sense_article:
            calcs.append(CalcDetectat(tipus="article_absent", text_original=match.group(), posicio=(match.start(), match.end()), explicacio="Possible falta d'article (calc del rus)", suggeriment="Afegir article definit o indefinit", severitat=5.0, llengua_origen=self.llengua))
            
        # Doble negació
        doble_neg = re.finditer(r'\b(ningú|res|mai|cap|enlloc)\s+no\b', text, re.IGNORECASE)
        for match in doble_neg:
            calcs.append(CalcDetectat(tipus="negacio_doble", text_original=match.group(), posicio=(match.start(), match.end()), explicacio="Doble negació", suggeriment="Verificar si la doble negació és natural aquí", severitat=3.0, llengua_origen=self.llengua))
            
        # Diminutius excessius
        diminutius = re.finditer(r'\b\w+(et|eta|ó|ona|ico|ica|illo|illa|ito|ita)\b.*\b\w+(et|eta|ó|ona|ico|ica)\b', text, re.IGNORECASE)
        for match in diminutius:
            calcs.append(CalcDetectat(tipus="calc_sintactic", text_original=match.group(), posicio=(match.start(), match.end()), explicacio="Possible excés de diminutius (calc del rus)", suggeriment="Reduir l'ús de diminutius", severitat=3.0, llengua_origen=self.llengua))
            
        return calcs
