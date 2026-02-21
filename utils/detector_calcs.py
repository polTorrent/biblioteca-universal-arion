"""Detector de calcs lingüístics per millorar la fluïdesa de traduccions.

Identifica construccions no naturals en català que són calcs de:
- Llatí: ablatius absoluts, hipèrbatons, participis
- Grec: partícules, ordre de paraules
- Alemany: verbs al final, compostos
- Francès: falsos amics
- Anglès: gerundis, passives
"""

import re
from enum import Enum

from pydantic import BaseModel, Field


class TipusCalc(str, Enum):
    """Tipus de calc detectat."""
    HIPERBATON = "hiperbaton"  # Ordre de paraules no natural
    ABLATIU_ABSOLUT = "ablatiu_absolut"  # "Dit això, marxà"
    PARTICIPI_PESAT = "participi_pesat"  # Construccions participials massa llargues
    PASSIVA_EXCESSIVA = "passiva_excessiva"  # "És dit per ell"
    GERUNDI_ANGLES = "gerundi_angles"  # "Estava sent fet"
    FALS_AMIC = "fals_amic"  # Paraules que semblen similars però signifiquen diferent
    CALC_SINTACTIC = "calc_sintactic"  # Estructura de frase copiada
    ARTICLE_ABSENT = "article_absent"  # Falta article (del rus, llatí)
    ARTICLE_SOBRER = "article_sobrer"  # Article innecessari
    VERB_FINAL = "verb_final"  # Verb al final (de l'alemany)
    COMPOST_EXCESSIU = "compost_excessiu"  # Paraules compostes massa llargues
    NEGACIO_DOBLE = "negacio_doble"  # Del llatí/grec
    PRONOM_REDUNDANT = "pronom_redundant"  # "Ell mateix ell va fer"
    CONNECTOR_LLATI = "connector_llati"  # "Certament", "En veritat"


class CalcDetectat(BaseModel):
    """Un calc detectat en el text."""
    tipus: TipusCalc
    text_original: str  # Fragment problemàtic
    posicio: tuple[int, int]  # (inici, final) en el text
    explicacio: str  # Per què és un calc
    suggeriment: str  # Alternativa natural en català
    severitat: float = Field(ge=0, le=10)  # 0-10, com de greu és
    llengua_origen: str | None = None  # D'on ve el calc


class ResultatDeteccio(BaseModel):
    """Resultat complet de la detecció."""
    text_analitzat: str
    llengua_origen: str
    calcs: list[CalcDetectat] = Field(default_factory=list)
    puntuacio_fluidesa: float = Field(ge=0, le=10)  # 10 = perfecte, 0 = ple de calcs
    resum: str = ""

    @property
    def num_calcs(self) -> int:
        return len(self.calcs)

    @property
    def te_problemes(self) -> bool:
        return len(self.calcs) > 0


class DetectorCalcs:
    """Detecta calcs lingüístics en traduccions al català."""

    # Patrons per detectar calcs (regex)
    PATRONS = {
        # LLATÍ
        TipusCalc.ABLATIU_ABSOLUT: [
            # "Dit això", "Fet el discurs", "Arribat el rei"
            (r'\b(Dit|Fet|Arribat|Vist|Sentit|Acabat|Començat)\s+(això|allò|el\s+\w+|la\s+\w+)\b',
             "Ablatiu absolut - estructura llatina",
             "Reformular amb 'després de', 'quan', 'un cop'"),
        ],
        TipusCalc.HIPERBATON: [
            # Adjectiu molt separat del nom
            (r'\b(molt|tan|massa|prou)\s+\w+\s+\w+\s+\w+\s+(era|és|fou|serà)\b',
             "Ordre de paraules no natural",
             "Apropar l'adjectiu al nom que modifica"),
        ],
        TipusCalc.PARTICIPI_PESAT: [
            # Participis amb molts complements
            (r'\b(havent|essent|tenint|fent)\s+\w+\s+\w+\s+\w+\s+\w+\b',
             "Construcció participial massa pesada",
             "Dividir en dues oracions o usar subordinada"),
        ],

        # ANGLÈS
        TipusCalc.PASSIVA_EXCESSIVA: [
            # "és fet per", "va ser dit per"
            (r'\b(és|va ser|fou|serà|ha estat)\s+\w+\s+per\s+(ell|ella|ells|elles|algú)\b',
             "Passiva amb agent - poc natural en català",
             "Usar veu activa o passiva reflexa"),
        ],
        TipusCalc.GERUNDI_ANGLES: [
            # "estava sent", "estaven sent"
            (r'\b(estava|estaven|estàvem)\s+sent\b',
             "Gerundi anglès (progressive)",
             "Usar imperfet simple o perífrasi adequada"),
        ],

        # CONNECTORS LLATINITZANTS
        TipusCalc.CONNECTOR_LLATI: [
            (r'\b(Certament|En veritat|Per consegüent|No obstant això|Així doncs)\b',
             "Connector massa formal/llatinitzant",
             "Usar connectors més naturals: 'És clar que', 'De fet', 'Per tant'"),
            (r'\b(el qual cosa|la qual cosa)\b',
             "Relatiu llatinitzant",
             "Usar 'cosa que', 'fet que', o reformular"),
        ],

        # ALEMANY
        TipusCalc.VERB_FINAL: [
            # Verb al final de subordinada (patró alemany)
            (r',\s+que\s+\w+\s+\w+\s+\w+\s+\w+\s+(havia|va|podia|volia)\b',
             "Verb massa al final (possible calc de l'alemany)",
             "Avançar el verb a posició més natural"),
        ],

        # GENERAL
        TipusCalc.NEGACIO_DOBLE: [
            (r'\b(no\s+\.\.\.\s+ni|ni\s+\.\.\.\s+no)\b',
             "Negació doble (del llatí/grec)",
             "Revisar si la doble negació és necessària en català"),
        ],
        TipusCalc.PRONOM_REDUNDANT: [
            (r'\b(ell\s+mateix\s+ell|ella\s+mateixa\s+ella)\b',
             "Pronom redundant",
             "Eliminar la repetició"),
        ],
    }

    # Falsos amics per llengua
    FALSOS_AMICS = {
        "llatí": {
            "actualmente": ("actualment", "ara, en aquest moment"),
            "eventualmente": ("eventualment", "possiblement, potser"),
        },
        "francès": {
            "atendre": ("attendre", "esperar"),
            "assistir": ("assister", "presenciar, ser present"),
            "demanar": ("demander", "preguntar"),
        },
        "anglès": {
            "realitzar": ("realize", "adonar-se"),
            "assumir": ("assume", "suposar"),
            "eventualment": ("eventually", "finalment, al capdavall"),
        },
        "castellà": {
            "desde": ("desde", "des de"),
            "entonces": ("entonces", "llavors, aleshores"),
            "luego": ("luego", "després"),
        },
        "rus": {
            "magazín": ("магазин", "botiga (no revista)"),
            "simpàtic": ("симпатичный", "agradable, bonic (no només simpàtic)"),
            "conductor": ("кондуктор", "revisor de tren (no qui condueix)"),
        },
        "japonès": {
            "manga": ("漫画", "còmic (no màniga)"),
            "anime": ("アニメ", "animació japonesa"),
        },
        "italià": {
            "burro": ("burro", "mantega (no ase)"),
            "camera": ("camera", "habitació (no càmera)"),
            "salir": ("salire", "pujar (no sortir)"),
            "caldo": ("caldo", "calent (no brou)"),
            "firma": ("firma", "empresa (no signatura)"),
        },
        "portuguès": {
            "polvo": ("polvo", "pop/polp (no pols)"),
            "exquisit": ("esquisito", "estrany (no delicat)"),
            "largo": ("largo", "ample (no llarg)"),
            "oficina": ("oficina", "taller (no despatx)"),
        },
        "xinès": {
            "tofu": ("豆腐", "formatge de soja"),
        },
        "àrab": {
            "alcalde": ("القاضي", "jutge en origen (ara batlle)"),
        },
    }

    # Expressions més naturals en català
    ALTERNATIVES_NATURALS = {
        "dit això": ["un cop dit això", "després d'això", "havent dit això"],
        "no obstant això": ["tanmateix", "malgrat tot", "amb tot"],
        "per consegüent": ["per tant", "així doncs", "en conseqüència"],
        "en veritat": ["de veritat", "realment", "de fet"],
        "certament": ["és clar", "sens dubte", "efectivament"],
    }

    def __init__(self, llengua_origen: str = "llatí"):
        """
        Args:
            llengua_origen: Llengua des de la qual s'ha traduït.
        """
        self.llengua_origen = llengua_origen.lower()

    def detectar(self, text: str) -> ResultatDeteccio:
        """Detecta calcs en un text traduït.

        Args:
            text: Text traduït al català a analitzar.

        Returns:
            ResultatDeteccio amb tots els calcs trobats.
        """
        calcs: list[CalcDetectat] = []

        # Detectar patrons per regex
        for tipus, patrons in self.PATRONS.items():
            for patro, explicacio, suggeriment in patrons:
                for match in re.finditer(patro, text, re.IGNORECASE):
                    calcs.append(CalcDetectat(
                        tipus=tipus,
                        text_original=match.group(),
                        posicio=(match.start(), match.end()),
                        explicacio=explicacio,
                        suggeriment=suggeriment,
                        severitat=self._calcular_severitat(tipus),
                        llengua_origen=self.llengua_origen,
                    ))

        # Detectar falsos amics
        calcs.extend(self._detectar_falsos_amics(text))

        # Detectar patrons específics per llengua
        calcs.extend(self._detectar_per_llengua(text))

        # Calcular puntuació de fluïdesa
        puntuacio = self._calcular_puntuacio(text, calcs)

        # Generar resum
        resum = self._generar_resum(calcs)

        return ResultatDeteccio(
            text_analitzat=text,
            llengua_origen=self.llengua_origen,
            calcs=calcs,
            puntuacio_fluidesa=puntuacio,
            resum=resum,
        )

    def _detectar_falsos_amics(self, text: str) -> list[CalcDetectat]:
        """Detecta falsos amics segons la llengua d'origen."""
        calcs = []

        # Buscar en totes les llengües per si de cas
        for llengua, amics in self.FALSOS_AMICS.items():
            for paraula_cat, (paraula_orig, significat_real) in amics.items():
                # Buscar la paraula en el text
                for match in re.finditer(rf'\b{paraula_cat}\b', text, re.IGNORECASE):
                    calcs.append(CalcDetectat(
                        tipus=TipusCalc.FALS_AMIC,
                        text_original=match.group(),
                        posicio=(match.start(), match.end()),
                        explicacio=f"Possible fals amic de '{paraula_orig}' ({llengua})",
                        suggeriment=f"Verificar si el significat és '{significat_real}'",
                        severitat=5.0,
                        llengua_origen=llengua,
                    ))

        return calcs

    def _detectar_per_llengua(self, text: str) -> list['CalcDetectat']:
        """Detecta patrons específics usant l'arquitectura de plugins."""
        from .calcs_plugins import obtenir_plugin
        calcs = []
        plugin = obtenir_plugin(self.llengua_origen)
        if plugin:
            res = plugin.detectar(text)
            for c in res:
                # Convertim el model del plugin al model principal
                calcs.append(CalcDetectat(
                    tipus=c.tipus,
                    text_original=c.text_original,
                    posicio=c.posicio,
                    explicacio=c.explicacio,
                    suggeriment=c.suggeriment,
                    severitat=c.severitat,
                    llengua_origen=c.llengua_origen
                ))
        return calcs

    def _calcular_severitat(self, tipus: TipusCalc) -> float:
        """Retorna la severitat base per tipus de calc."""
        severitats = {
            TipusCalc.HIPERBATON: 6.0,
            TipusCalc.ABLATIU_ABSOLUT: 5.0,
            TipusCalc.PARTICIPI_PESAT: 5.0,
            TipusCalc.PASSIVA_EXCESSIVA: 7.0,
            TipusCalc.GERUNDI_ANGLES: 8.0,
            TipusCalc.FALS_AMIC: 6.0,
            TipusCalc.CALC_SINTACTIC: 4.0,
            TipusCalc.ARTICLE_ABSENT: 5.0,
            TipusCalc.ARTICLE_SOBRER: 4.0,
            TipusCalc.VERB_FINAL: 5.0,
            TipusCalc.COMPOST_EXCESSIU: 4.0,
            TipusCalc.NEGACIO_DOBLE: 3.0,
            TipusCalc.PRONOM_REDUNDANT: 4.0,
            TipusCalc.CONNECTOR_LLATI: 3.0,
        }
        return severitats.get(tipus, 5.0)

    def _calcular_puntuacio(self, text: str, calcs: list[CalcDetectat]) -> float:
        """Calcula puntuació de fluïdesa (10 = perfecte).

        CALIBRACIÓ: Textos més llargs toleren més calcs (densitat).
        Un calc greu cada 200 paraules és acceptable.
        """
        if not calcs:
            return 10.0

        paraules = len(text.split())

        # Calcular DENSITAT de calcs (calcs per 100 paraules)
        densitat = (len(calcs) / max(paraules, 1)) * 100

        # Calcular severitat mitjana
        severitat_mitjana = sum(c.severitat for c in calcs) / len(calcs)

        # Penalització per densitat (escala logarítmica per evitar penalitzacions extremes)
        # - 0 calcs/100p = 10 punts
        # - 1 calc/100p = ~9 punts (acceptable)
        # - 2 calcs/100p = ~7.5 punts (notar)
        # - 5 calcs/100p = ~5 punts (problemàtic)
        # - 10+ calcs/100p = <3 punts (crític)
        import math
        penalitzacio_densitat = min(7.0, densitat * 1.2 + math.log1p(densitat) * 0.5)

        # Factor de severitat (multiplicador 0.8-1.2)
        factor_severitat = 0.8 + (severitat_mitjana / 10) * 0.4

        # Penalització total
        penalitzacio_total = penalitzacio_densitat * factor_severitat

        # Calcular puntuació base
        puntuacio = 10.0 - penalitzacio_total

        # Caps durs per NOMBRE ABSOLUT de calcs (independent de densitat)
        # Perquè fins i tot en textos llargs, massa calcs és problemàtic
        num_calcs = len(calcs)
        if num_calcs >= 10:
            puntuacio = min(puntuacio, 4.5)  # Massa calcs
        elif num_calcs >= 8:
            puntuacio = min(puntuacio, 5.5)
        elif num_calcs >= 5:
            puntuacio = min(puntuacio, 6.5)
        elif num_calcs >= 3:
            puntuacio = min(puntuacio, 7.5)

        return max(0.0, min(10.0, round(puntuacio, 1)))

    def _generar_resum(self, calcs: list[CalcDetectat]) -> str:
        """Genera un resum dels calcs detectats."""
        if not calcs:
            return "No s'han detectat calcs lingüístics. El text sembla natural en català."

        # Comptar per tipus
        per_tipus: dict[TipusCalc, int] = {}
        for calc in calcs:
            per_tipus[calc.tipus] = per_tipus.get(calc.tipus, 0) + 1

        linies = [f"Detectats {len(calcs)} possibles calcs:"]
        for tipus, count in sorted(per_tipus.items(), key=lambda x: -x[1]):
            linies.append(f"  - {tipus.value}: {count}")

        return "\n".join(linies)


def detectar_calcs(text: str, llengua_origen: str = "llatí") -> ResultatDeteccio:
    """Funció helper per detectar calcs.

    Ús:
        from utils.detector_calcs import detectar_calcs
        resultat = detectar_calcs("Dit això, el rei marxà.", "llatí")
        print(f"Fluïdesa: {resultat.puntuacio_fluidesa}/10")
        for calc in resultat.calcs:
            print(f"  - {calc.tipus}: {calc.text_original}")
    """
    detector = DetectorCalcs(llengua_origen)
    return detector.detectar(text)
