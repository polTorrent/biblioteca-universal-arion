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

    def _detectar_per_llengua(self, text: str) -> list[CalcDetectat]:
        """Detecta patrons específics segons la llengua d'origen."""
        calcs = []
        llengua = self.llengua_origen.lower()

        if llengua in ["llatí", "llati", "latin", "la"]:
            calcs.extend(self._detectar_calcs_llati(text))
        elif llengua in ["grec", "greek", "grc", "griego"]:
            calcs.extend(self._detectar_calcs_grec(text))
        elif llengua in ["alemany", "german", "de", "deutsch"]:
            calcs.extend(self._detectar_calcs_alemany(text))
        elif llengua in ["anglès", "anglés", "english", "en"]:
            calcs.extend(self._detectar_calcs_angles(text))
        elif llengua in ["rus", "russian", "ru", "ruso"]:
            calcs.extend(self._detectar_calcs_rus(text))
        elif llengua in ["japonès", "japones", "japanese", "ja", "japonés"]:
            calcs.extend(self._detectar_calcs_japones(text))
        elif llengua in ["àrab", "arab", "arabic", "ar", "árabe"]:
            calcs.extend(self._detectar_calcs_arab(text))
        elif llengua in ["xinès", "xines", "chinese", "zh", "chino"]:
            calcs.extend(self._detectar_calcs_xines(text))
        elif llengua in ["italià", "italia", "italian", "it", "italiano"]:
            calcs.extend(self._detectar_calcs_romanic(text, "italià"))
        elif llengua in ["portuguès", "portugues", "portuguese", "pt", "portugués"]:
            calcs.extend(self._detectar_calcs_romanic(text, "portuguès"))

        return calcs

    def _detectar_calcs_llati(self, text: str) -> list[CalcDetectat]:
        """Patrons específics del llatí."""
        calcs = []

        # Acusatiu amb infinitiu ("Dic que ell ser bo" -> "Dic que ell és bo")
        # Genitiu partitiu ("molts dels homes" vs "molts homes")
        partitiu = re.finditer(r'\b(molts|alguns|pocs|cap)\s+dels?\s+\w+', text, re.IGNORECASE)
        for match in partitiu:
            calcs.append(CalcDetectat(
                tipus=TipusCalc.CALC_SINTACTIC,
                text_original=match.group(),
                posicio=(match.start(), match.end()),
                explicacio="Possible genitiu partitiu llatí",
                suggeriment="Considerar eliminar 'dels/de les' si no és necessari",
                severitat=3.0,
                llengua_origen="llatí",
            ))

        return calcs

    def _detectar_calcs_grec(self, text: str) -> list[CalcDetectat]:
        """Patrons específics del grec."""
        calcs = []

        # μέν...δέ -> "per una banda... per l'altra"
        men_de = re.search(r'per una banda.{5,50}per l\'altra', text, re.IGNORECASE)
        if men_de:
            calcs.append(CalcDetectat(
                tipus=TipusCalc.CALC_SINTACTIC,
                text_original=men_de.group(),
                posicio=(men_de.start(), men_de.end()),
                explicacio="Possible calc de μέν...δέ grec",
                suggeriment="Valorar si l'estructura és necessària o simplificar",
                severitat=4.0,
                llengua_origen="grec",
            ))

        return calcs

    def _detectar_calcs_alemany(self, text: str) -> list[CalcDetectat]:
        """Patrons específics de l'alemany."""
        calcs = []

        # Compostos molt llargs
        compostos = re.finditer(r'\b\w{20,}\b', text)
        for match in compostos:
            calcs.append(CalcDetectat(
                tipus=TipusCalc.COMPOST_EXCESSIU,
                text_original=match.group(),
                posicio=(match.start(), match.end()),
                explicacio="Paraula composta molt llarga (possible calc de l'alemany)",
                suggeriment="Considerar separar en diverses paraules",
                severitat=4.0,
                llengua_origen="alemany",
            ))

        return calcs

    def _detectar_calcs_angles(self, text: str) -> list[CalcDetectat]:
        """Patrons específics de l'anglès."""
        calcs = []

        # Gerundi com a subjecte excessiu
        gerundi_subjecte = re.finditer(
            r'\b(El|La)\s+(nedar|córrer|llegir|escriure|caminar|menjar)\s+(és|resulta)\b',
            text, re.IGNORECASE
        )
        for match in gerundi_subjecte:
            calcs.append(CalcDetectat(
                tipus=TipusCalc.GERUNDI_ANGLES,
                text_original=match.group(),
                posicio=(match.start(), match.end()),
                explicacio="Gerundi com a subjecte (calc de l'anglès)",
                suggeriment="Considerar infinitiu o reformular",
                severitat=4.0,
                llengua_origen="anglès",
            ))

        return calcs

    def _detectar_calcs_rus(self, text: str) -> list[CalcDetectat]:
        """Patrons específics del rus."""
        calcs = []

        # Absència d'article on caldria
        # "Home va al mercat" vs "L'home va al mercat"
        sense_article = re.finditer(
            r'\b(Home|Dona|Nen|Nena|Noia|Noi|Gat|Gos|Llibre|Taula|Cadira|Cotxe|Casa)\s+'
            r'(va|és|té|fa|estava|anava|tenia|feia|vol|pot|ha)\b',
            text
        )
        for match in sense_article:
            calcs.append(CalcDetectat(
                tipus=TipusCalc.ARTICLE_ABSENT,
                text_original=match.group(),
                posicio=(match.start(), match.end()),
                explicacio="Possible falta d'article (calc del rus)",
                suggeriment="Afegir article definit o indefinit: 'L'home', 'Un home'",
                severitat=5.0,
                llengua_origen="rus",
            ))

        # Doble negació russa (ningú no, res no, mai no)
        doble_neg = re.finditer(r'\b(ningú|res|mai|cap|enlloc)\s+no\b', text, re.IGNORECASE)
        for match in doble_neg:
            calcs.append(CalcDetectat(
                tipus=TipusCalc.NEGACIO_DOBLE,
                text_original=match.group(),
                posicio=(match.start(), match.end()),
                explicacio="Doble negació (natural en rus, revisar en català)",
                suggeriment="Verificar si la doble negació és natural aquí",
                severitat=3.0,
                llengua_origen="rus",
            ))

        # Diminutius excessius (típics del rus)
        diminutius = re.finditer(
            r'\b\w+(et|eta|ó|ona|ico|ica|illo|illa|ito|ita)\b.*\b\w+(et|eta|ó|ona|ico|ica)\b',
            text, re.IGNORECASE
        )
        for match in diminutius:
            calcs.append(CalcDetectat(
                tipus=TipusCalc.CALC_SINTACTIC,
                text_original=match.group(),
                posicio=(match.start(), match.end()),
                explicacio="Possible excés de diminutius (calc del rus)",
                suggeriment="Reduir l'ús de diminutius si no són necessaris",
                severitat=3.0,
                llengua_origen="rus",
            ))

        return calcs

    def _detectar_calcs_japones(self, text: str) -> list[CalcDetectat]:
        """Patrons específics del japonès."""
        calcs = []

        # Verb massa al final (SOV japonès)
        # Patró: subjecte + complements + verb al final de la frase
        verb_final = re.finditer(
            r'[^.!?]+\s+(fer|dir|anar|venir|poder|voler|saber|tenir|estar|ser)\s*[.!?]',
            text
        )
        for match in verb_final:
            # Només si hi ha prou paraules abans del verb
            paraules_abans = len(match.group().split()) - 1
            if paraules_abans >= 5:
                calcs.append(CalcDetectat(
                    tipus=TipusCalc.VERB_FINAL,
                    text_original=match.group().strip(),
                    posicio=(match.start(), match.end()),
                    explicacio="Verb al final de frase (ordre SOV japonès)",
                    suggeriment="Reorganitzar a ordre SVO català natural",
                    severitat=6.0,
                    llengua_origen="japonès",
                ))

        # Topicalització excessiva (partícula は wa)
        tema_wa = re.finditer(
            r'\b(Quant a|Pel que fa a|Respecte a|Sobre)\s+\w+(\s+\w+)?,',
            text
        )
        for match in tema_wa:
            calcs.append(CalcDetectat(
                tipus=TipusCalc.CALC_SINTACTIC,
                text_original=match.group(),
                posicio=(match.start(), match.end()),
                explicacio="Possible calc de la partícula は (wa) japonesa",
                suggeriment="Considerar reformular sense topicalització explícita",
                severitat=3.0,
                llengua_origen="japonès",
            ))

        # Passiva de perjudici (迷惑の受身)
        passiva_perjudici = re.finditer(
            r'\b(em|et|li|ens|us|els)\s+(van|va|han|ha)\s+(ser|estar)\s+\w+',
            text, re.IGNORECASE
        )
        for match in passiva_perjudici:
            calcs.append(CalcDetectat(
                tipus=TipusCalc.PASSIVA_EXCESSIVA,
                text_original=match.group(),
                posicio=(match.start(), match.end()),
                explicacio="Possible passiva de perjudici (calc del japonès)",
                suggeriment="Considerar reformular en veu activa",
                severitat=5.0,
                llengua_origen="japonès",
            ))

        # Onomatopeies no adaptades (patrons repetitius)
        onomatopeia = re.finditer(r'\b(\w{2,3})-\1\b', text)
        for match in onomatopeia:
            calcs.append(CalcDetectat(
                tipus=TipusCalc.CALC_SINTACTIC,
                text_original=match.group(),
                posicio=(match.start(), match.end()),
                explicacio="Possible onomatopeia japonesa no adaptada",
                suggeriment="Adaptar a equivalent català o descriure l'efecte",
                severitat=4.0,
                llengua_origen="japonès",
            ))

        return calcs

    def _detectar_calcs_arab(self, text: str) -> list[CalcDetectat]:
        """Patrons específics de l'àrab."""
        calcs = []

        # Frases sense verb "ser" (l'àrab no usa còpula al present)
        # "El llibre gran" vs "El llibre és gran"
        sense_copula = re.finditer(
            r'\b(El|La|Els|Les|Un|Una)\s+\w+\s+'
            r'(molt\s+)?(gran|petit|bo|dolent|bell|lleig|nou|vell|alt|baix|ric|pobre)\b',
            text
        )
        for match in sense_copula:
            fragment = match.group()
            if " és " not in fragment and " són " not in fragment and " era " not in fragment:
                calcs.append(CalcDetectat(
                    tipus=TipusCalc.CALC_SINTACTIC,
                    text_original=fragment,
                    posicio=(match.start(), match.end()),
                    explicacio="Possible frase nominal sense còpula (calc de l'àrab)",
                    suggeriment="Afegir verb 'ser' si és una oració copulativa",
                    severitat=4.0,
                    llengua_origen="àrab",
                ))

        # Ordre VSO (verb-subjecte-objecte) típic de l'àrab
        vso = re.finditer(
            r'\b(Va|Anà|Digué|Féu|Vingué|Sortí|Entrà)\s+(el|la|l\')\s+\w+\s+',
            text
        )
        for match in vso:
            calcs.append(CalcDetectat(
                tipus=TipusCalc.CALC_SINTACTIC,
                text_original=match.group(),
                posicio=(match.start(), match.end()),
                explicacio="Ordre VSO (calc de l'àrab)",
                suggeriment="Considerar ordre SVO: 'El rei va dir' en lloc de 'Va dir el rei'",
                severitat=4.0,
                llengua_origen="àrab",
            ))

        # Estat constructe (idafa) amb "de" excessiu
        idafa = re.finditer(r'\b(la casa de l\'home de la ciutat)\b', text, re.IGNORECASE)
        for match in idafa:
            calcs.append(CalcDetectat(
                tipus=TipusCalc.CALC_SINTACTIC,
                text_original=match.group(),
                posicio=(match.start(), match.end()),
                explicacio="Possible cadena d'estat constructe (idafa)",
                suggeriment="Simplificar la cadena de genitius",
                severitat=4.0,
                llengua_origen="àrab",
            ))

        return calcs

    def _detectar_calcs_xines(self, text: str) -> list[CalcDetectat]:
        """Patrons específics del xinès."""
        calcs = []

        # Classificadors traduïts literalment
        classificadors = re.finditer(
            r'\b(un cap de|una boca de|un ull de|una mà de|un tros de persona)\b',
            text, re.IGNORECASE
        )
        for match in classificadors:
            calcs.append(CalcDetectat(
                tipus=TipusCalc.CALC_SINTACTIC,
                text_original=match.group(),
                posicio=(match.start(), match.end()),
                explicacio="Possible classificador xinès traduït literalment",
                suggeriment="Adaptar a forma natural en català",
                severitat=5.0,
                llengua_origen="xinès",
            ))

        # Estructura tema-comentari excessiva
        tema_comentari = re.finditer(
            r'\b(Aquesta cosa|Aquest assumpte|Aquell tema),\s*jo\s+',
            text
        )
        for match in tema_comentari:
            calcs.append(CalcDetectat(
                tipus=TipusCalc.CALC_SINTACTIC,
                text_original=match.group(),
                posicio=(match.start(), match.end()),
                explicacio="Estructura tema-comentari (calc del xinès)",
                suggeriment="Reformular amb estructura catalana natural",
                severitat=4.0,
                llengua_origen="xinès",
            ))

        # Repetició de verbs per èmfasi (很很 -> molt molt)
        repeticio_emfasi = re.finditer(r'\b(molt molt|ben bé|poc poc)\b', text, re.IGNORECASE)
        for match in repeticio_emfasi:
            calcs.append(CalcDetectat(
                tipus=TipusCalc.CALC_SINTACTIC,
                text_original=match.group(),
                posicio=(match.start(), match.end()),
                explicacio="Repetició per èmfasi (calc del xinès)",
                suggeriment="Usar superlatius o intensificadors catalans",
                severitat=3.0,
                llengua_origen="xinès",
            ))

        return calcs

    def _detectar_calcs_romanic(self, text: str, llengua: str) -> list[CalcDetectat]:
        """Patrons específics de llengües romàniques (italià, portuguès)."""
        calcs = []

        # Gerundis mal usats (diferent ús que en català)
        gerundi_incorrecte = re.finditer(
            r'\b(estic|estàs|està|estem|esteu|estan)\s+\w+ant\b',
            text, re.IGNORECASE
        )
        for match in gerundi_incorrecte:
            calcs.append(CalcDetectat(
                tipus=TipusCalc.GERUNDI_ANGLES,
                text_original=match.group(),
                posicio=(match.start(), match.end()),
                explicacio=f"Perífrasi de gerundi (revisar si és natural en català, calc de {llengua})",
                suggeriment="Considerar usar present simple o altres perífrasis",
                severitat=3.0,
                llengua_origen=llengua,
            ))

        # Preposicions mal usades (a personal, per, etc.)
        if llengua == "italià":
            # "a" personal italiana
            a_personal = re.finditer(r'\bveig a (la|el|l\')\s+\w+\b', text, re.IGNORECASE)
            for match in a_personal:
                calcs.append(CalcDetectat(
                    tipus=TipusCalc.CALC_SINTACTIC,
                    text_original=match.group(),
                    posicio=(match.start(), match.end()),
                    explicacio="Possible 'a' personal (calc de l'italià)",
                    suggeriment="En català no s'usa 'a' personal amb objectes directes",
                    severitat=5.0,
                    llengua_origen=llengua,
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
        """Calcula puntuació de fluïdesa (10 = perfecte)."""
        if not calcs:
            return 10.0

        # Penalitzar segons nombre i severitat
        penalitzacio = sum(c.severitat * 0.1 for c in calcs)

        # Ajustar per longitud del text (més text = més tolerància)
        paraules = len(text.split())
        factor_longitud = min(1.0, paraules / 100)  # Normalitzar

        puntuacio = 10.0 - (penalitzacio * factor_longitud)
        return max(0.0, min(10.0, puntuacio))

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
