import re
from typing import List
from .base import DetectorPlugin, CalcDetectat

class DetectorJapones(DetectorPlugin):
    @property
    def llengua(self) -> str:
        return "japonès"
        
    def detectar(self, text: str) -> List[CalcDetectat]:
        calcs = []
        verb_final = re.finditer(r'[^.!?]+\s+(fer|dir|anar|venir|poder|voler|saber|tenir|estar|ser)\s*[.!?]', text)
        for match in verb_final:
            paraules_abans = len(match.group().split()) - 1
            if paraules_abans >= 5:
                calcs.append(CalcDetectat(tipus="verb_final", text_original=match.group().strip(), posicio=(match.start(), match.end()), explicacio="Verb al final de frase (ordre SOV japonès)", suggeriment="Reorganitzar a ordre SVO català natural", severitat=6.0, llengua_origen=self.llengua))
                
        tema_wa = re.finditer(r'\b(Quant a|Pel que fa a|Respecte a|Sobre)\s+\w+(\s+\w+)?,', text)
        for match in tema_wa:
            calcs.append(CalcDetectat(tipus="calc_sintactic", text_original=match.group(), posicio=(match.start(), match.end()), explicacio="Possible calc de la partícula は (wa) japonesa", suggeriment="Considerar reformular sense topicalització explícita", severitat=3.0, llengua_origen=self.llengua))
            
        passiva_perjudici = re.finditer(r'\b(em|et|li|ens|us|els)\s+(van|va|han|ha)\s+(ser|estar)\s+\w+', text, re.IGNORECASE)
        for match in passiva_perjudici:
            calcs.append(CalcDetectat(tipus="passiva_excessiva", text_original=match.group(), posicio=(match.start(), match.end()), explicacio="Possible passiva de perjudici (calc del japonès)", suggeriment="Considerar reformular en veu activa", severitat=5.0, llengua_origen=self.llengua))

        onomatopeia = re.finditer(r'\b(\w{2,3})-\1\b', text)
        for match in onomatopeia:
            calcs.append(CalcDetectat(tipus="calc_sintactic", text_original=match.group(), posicio=(match.start(), match.end()), explicacio="Possible onomatopeia japonesa no adaptada", suggeriment="Adaptar a equivalent català o descriure l'efecte", severitat=4.0, llengua_origen=self.llengua))
            
        return calcs
