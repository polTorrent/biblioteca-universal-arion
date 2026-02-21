import re
from typing import List
from .base import DetectorPlugin, CalcDetectat

class DetectorAngles(DetectorPlugin):
    @property
    def llengua(self) -> str:
        return "anglès"
        
    def detectar(self, text: str) -> List[CalcDetectat]:
        calcs = []
        
        # Expressions idiomàtiques calcades
        expressions = [
            (r'\b[Pp]er totes les aparences\b', "«Per totes les aparences» (By all appearances)", "Usar «Tot indicava que», «A primer cop d'ull»", 7.0),
            (r'\bmés aviat que no pas\b', "«més aviat que no pas» (rather than)", "Usar «en lloc de», «per no»", 6.0),
            (r'\ba fi de\b', "«a fi de» (in order to)", "Simplificar a «per» o «per tal de»", 4.0),
            (r'\bcom a qüestió de fet\b', "«com a qüestió de fet» (as a matter of fact)", "Usar «de fet», «en realitat»", 6.0),
            (r'\bal mateix temps que\b', "«al mateix temps que» calc literal", "Valorar «alhora que», «mentre»", 4.0),
            (r'\b(va |van )?(prendre|tenir) lloc\b', "«prendre/tenir lloc» (to take place)", "Usar «passar», «ocórrer»", 5.0),
            (r'\b(fer|feia|fa) sentit\b', "«fer sentit» (to make sense)", "Usar «tenir sentit», «ser lògic»", 6.0),
            (r'\bresulta que\b', "«resulta que» (it turns out)", "Valorar «s'esdevé que», «passa que»", 3.0),
        ]
        for patro, explicacio, suggeriment, severitat in expressions:
            for match in re.finditer(patro, text, re.IGNORECASE):
                calcs.append(CalcDetectat(tipus="calc_sintactic", text_original=match.group(), posicio=(match.start(), match.end()), explicacio=explicacio, suggeriment=suggeriment, severitat=severitat, llengua_origen=self.llengua))
                
        # Passiva amb agent
        passiva = re.finditer(r'\b(va ser|fou|ha estat|havia estat|serà)\s+\w+(at|it|ut|ada|ida|uda)\s+per\s+', text, re.IGNORECASE)
        for match in passiva:
            calcs.append(CalcDetectat(tipus="passiva_excessiva", text_original=match.group(), posicio=(match.start(), match.end()), explicacio="Passiva amb agent explícit", suggeriment="Preferir veu activa o passiva reflexa", severitat=6.0, llengua_origen=self.llengua))
            
        # Gerundi progressiu
        progressiu = re.finditer(r'\b(estava|estaven|estic|estàs|està|estem|esteu|estan)\s+\w+(ant|ent|int)\b', text, re.IGNORECASE)
        for match in progressiu:
            calcs.append(CalcDetectat(tipus="gerundi_angles", text_original=match.group(), posicio=(match.start(), match.end()), explicacio="Perífrasi progressiva (I am doing)", suggeriment="Valorar imperfet simple", severitat=4.0, llengua_origen=self.llengua))

        return calcs
