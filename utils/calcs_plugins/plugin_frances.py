from typing import List
import re
from .base import DetectorPlugin, CalcDetectat, TipusCalc

class DetectorFrances(DetectorPlugin):
    @property
    def llengua(self) -> str:
        return "francès"

    def detectar(self, text: str) -> List[CalcDetectat]:
        resultats = []
        falsos_amics = {
            r"\bentendre\b": ("escoltar", "Fals amic 'entendre' (francès) en comptes d''escoltar'."),
            r"\battendre\b": ("esperar", "Fals amic 'attendre' (francès) per 'esperar'."),
            r"\bsubir\b": ("patir", "Fals amic 'subir' (francès) per 'patir' o 'sofrir'."),
            r"\brester\b": ("quedar-se", "Fals amic 'rester' (francès) per 'quedar-se'."),
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
                    severitat=7.0,
                    llengua_origen="fr"
                ))
        return resultats
