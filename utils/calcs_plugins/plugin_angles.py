from __future__ import annotations

import re
from .base import DetectorPlugin, CalcDetectat

class DetectorAngles(DetectorPlugin):
    @property
    def llengua(self) -> str:
        return "anglès"
        
    def detectar(self, text: str) -> list[CalcDetectat]:
        calcs = []
        
        # Expressions idiomàtiques calcades
        expressions = [
            (r'\bper totes les aparences\b', "«Per totes les aparences» (By all appearances)", "Usar «Tot indicava que», «A primer cop d'ull»", 7.0),
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
                
        # "manar" com a calc de l'anglès "to bid/command" (hauria de ser "demanar")
        manar = re.finditer(r'\b(vaig|vas|va|vam|vau|van)\s+manar\b', text, re.IGNORECASE)
        for match in manar:
            calcs.append(CalcDetectat(tipus="calc_sintactic", text_original=match.group(), posicio=(match.start(), match.end()), explicacio="«manar» calc de l'anglès 'to bid/command'", suggeriment="Usar «demanar», «ordenar»", severitat=6.0, llengua_origen=self.llengua))

        # Repetició d'adverbi amb guió llarg (Long—long, calc de l'anglès)
        repeticio = re.finditer(r'\b(\w{4,})\s*[—–-]\s*\1\b', text, re.IGNORECASE)
        for match in repeticio:
            calcs.append(CalcDetectat(tipus="calc_sintactic", text_original=match.group(), posicio=(match.start(), match.end()), explicacio="Repetició d'adverbi amb guió (calc de l'anglès)", suggeriment="Usar «durant molt de temps», «intensament»", severitat=6.0, llengua_origen=self.llengua))

        # "just + verb" calc de l'anglès "just becoming"
        just_verb = re.finditer(r'\bjust\s+\w+(ia|ava|eix|enia|eva)\b', text, re.IGNORECASE)
        for match in just_verb:
            calcs.append(CalcDetectat(tipus="calc_sintactic", text_original=match.group(), posicio=(match.start(), match.end()), explicacio="«just + verb» calc de l'anglès", suggeriment="Usar «tot just», «acabava de», «just en aquell moment»", severitat=5.0, llengua_origen=self.llengua))

        # Lèxic forçat / arcaic (paraules poc naturals en català modern)
        lexic_forcat = [
            (r'\bvivaces\b', "«vivaces» lèxic forçat/calc", "Usar «vius», «vívids», «animats»", 5.0),
            (r'\besquinçades\b', "«esquinçades» ús forçat en context decoratiu", "Valorar «esguerrades», «trencades», «malmeses»", 5.0),
            (r'\bfornícula\b', "«fornícula» mot arcaic/forçat", "Usar «nínxol», «fornícula» només si és tècnic", 5.0),
        ]
        for patro, explicacio, suggeriment, severitat in lexic_forcat:
            for match in re.finditer(patro, text, re.IGNORECASE):
                calcs.append(CalcDetectat(tipus="fals_amic", text_original=match.group(), posicio=(match.start(), match.end()), explicacio=explicacio, suggeriment=suggeriment, severitat=severitat, llengua_origen=self.llengua))

        # Passiva amb agent
        passiva = re.finditer(r'\b(va ser|fou|ha estat|havia estat|serà)\s+\w+(at|it|ut|ada|ida|uda)\s+per\s+', text, re.IGNORECASE)
        for match in passiva:
            calcs.append(CalcDetectat(tipus="passiva_excessiva", text_original=match.group(), posicio=(match.start(), match.end()), explicacio="Passiva amb agent explícit", suggeriment="Preferir veu activa o passiva reflexa", severitat=6.0, llengua_origen=self.llengua))
            
        # Gerundi progressiu
        progressiu = re.finditer(r'\b(estava|estaven|estic|estàs|està|estem|esteu|estan)\s+\w+(ant|ent|int)\b', text, re.IGNORECASE)
        for match in progressiu:
            calcs.append(CalcDetectat(tipus="gerundi_angles", text_original=match.group(), posicio=(match.start(), match.end()), explicacio="Perífrasi progressiva (I am doing)", suggeriment="Valorar imperfet simple", severitat=4.0, llengua_origen=self.llengua))

        return calcs
