import re
from typing import List
from .base import DetectorPlugin, CalcDetectat

class DetectorArab(DetectorPlugin):
    @property
    def llengua(self) -> str:
        return "àrab"
        
    def detectar(self, text: str) -> List[CalcDetectat]:
        calcs = []
        sense_copula = re.finditer(r'\b(El|La|Els|Les|Un|Una)\s+\w+\s+(molt\s+)?(gran|petit|bo|dolent|bell|lleig|nou|vell|alt|baix|ric|pobre)\b', text)
        for match in sense_copula:
            fragment = match.group()
            if " és " not in fragment and " són " not in fragment and " era " not in fragment:
                calcs.append(CalcDetectat(tipus="calc_sintactic", text_original=fragment, posicio=(match.start(), match.end()), explicacio="Possible frase nominal sense còpula (calc de l'àrab)", suggeriment="Afegir verb 'ser'", severitat=4.0, llengua_origen=self.llengua))
                
        vso = re.finditer(r'\b(Va|Anà|Digué|Féu|Vingué|Sortí|Entrà)\s+(el|la|l\')\s+\w+\s+', text)
        for match in vso:
            calcs.append(CalcDetectat(tipus="calc_sintactic", text_original=match.group(), posicio=(match.start(), match.end()), explicacio="Ordre VSO (calc de l'àrab)", suggeriment="Considerar ordre SVO", severitat=4.0, llengua_origen=self.llengua))
            
        idafa = re.finditer(r'\b(la casa de l\'home de la ciutat)\b', text, re.IGNORECASE)
        for match in idafa:
            calcs.append(CalcDetectat(tipus="calc_sintactic", text_original=match.group(), posicio=(match.start(), match.end()), explicacio="Possible cadena d'estat constructe", suggeriment="Simplificar", severitat=4.0, llengua_origen=self.llengua))
            
        return calcs
