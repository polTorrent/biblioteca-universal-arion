"""Agent de Disseny Gràfic per definir l'estil visual de les publicacions."""

from typing import Literal

from pydantic import BaseModel, Field

from agents.base_agent import AgentConfig, AgentResponse, BaseAgent


class Typography(BaseModel):
    """Especificacions tipogràfiques."""

    font_principal: str
    font_titols: str
    font_notes: str
    mida_cos: str
    mida_titols: str
    interlineat: str


class ColorPalette(BaseModel):
    """Paleta de colors."""

    primari: str
    secundari: str
    accent: str
    text: str
    fons: str


class DesignSpec(BaseModel):
    """Especificacions de disseny complet."""

    tipografia: Typography
    colors: ColorPalette
    marges: dict[str, str]
    estil_notes: str
    estil_titols: str


class DesignRequest(BaseModel):
    """Sol·licitud de disseny."""

    titol: str
    autor: str
    colleccio: str = "Clàssics Catalans"
    estil: Literal["clàssic", "modern", "minimalista"] = "clàssic"
    format_principal: Literal["epub", "pdf", "ambdós"] = "epub"
    bilingue: bool = True


class DissenyGraficAgent(BaseAgent):
    """Agent per definir l'estil visual de les publicacions.

    Crea especificacions de disseny i CSS per a EPUB i PDF.
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        estil: Literal["clàssic", "modern", "minimalista"] = "clàssic",
    ) -> None:
        super().__init__(config)
        self.estil = estil

    @property
    def system_prompt(self) -> str:
        return f"""Ets un dissenyador editorial expert en publicacions de textos clàssics.

OBJECTIU:
Crear especificacions de disseny elegants i llegibles per a edicions de clàssics grecollatins en català.

ESTIL DE LA COL·LECCIÓ: {self.estil.upper()}

PRINCIPIS DE DISSENY EDITORIAL:

1. TIPOGRAFIA
   - Cos del text: Serif elegant i llegible (Georgia, Palatino, EB Garamond)
   - Títols: Poden ser serif o sans-serif amb personalitat
   - Notes: Mida més petita, possible sans-serif
   - Text grec: Suport Unicode complet (GFS Didot, Gentium)
   - Text llatí: El mateix que el cos

2. PALETA DE COLORS (segons estil)
   - CLÀSSIC: Tons ocres, bordeus, or vell
   - MODERN: Contrast alt, accents vius
   - MINIMALISTA: Escala de grisos, un accent

3. MAQUETACIÓ
   - Marges generosos (especialment interior per enquadernació)
   - Línies de 60-75 caràcters per línia
   - Interlineat 1.4-1.6 per a lectura còmoda
   - Notes a peu de pàgina amb separador subtil

4. ELEMENTS ESPECIALS
   - Capitulars per a inici de capítols
   - Ornaments discrets entre seccions
   - Encapçalaments amb títol/autor
   - Numeració de pàgines elegant

5. FORMAT BILINGÜE
   - Original a l'esquerra, traducció a la dreta (enfrontat)
   - O original en cursiva seguit de traducció
   - Numeració de versos/línies visible

FORMAT DE RESPOSTA:
{{
    "especificacions": {{
        "tipografia": {{
            "font_principal": "<nom de la font>",
            "font_titols": "<nom de la font>",
            "font_notes": "<nom de la font>",
            "font_grec": "<nom de la font>",
            "mida_cos": "<mida>",
            "mida_titols": {{
                "h1": "<mida>",
                "h2": "<mida>",
                "h3": "<mida>"
            }},
            "interlineat": "<valor>"
        }},
        "colors": {{
            "primari": "<hex>",
            "secundari": "<hex>",
            "accent": "<hex>",
            "text": "<hex>",
            "fons": "<hex>",
            "enllaços": "<hex>"
        }},
        "maquetacio": {{
            "marge_superior": "<valor>",
            "marge_inferior": "<valor>",
            "marge_interior": "<valor>",
            "marge_exterior": "<valor>",
            "amplada_maxima": "<valor>"
        }},
        "elements": {{
            "capitulars": "<descripció>",
            "separadors": "<descripció>",
            "encapcalaments": "<descripció>",
            "notes_peu": "<descripció>"
        }}
    }},
    "css_epub": "<codi CSS complet per a EPUB>",
    "instruccions_portada": {{
        "estil": "<descripció de l'estil visual>",
        "elements": ["<element a incloure>"],
        "colors_recomanats": ["<hex>"],
        "tipografia_titol": "<font i estil>"
    }},
    "notes_implementacio": ["<consell pràctic>"]
}}"""

    def create_design(self, request: DesignRequest) -> AgentResponse:
        """Crea especificacions de disseny completes.

        Args:
            request: Paràmetres del disseny.

        Returns:
            AgentResponse amb especificacions i CSS.
        """
        self.estil = request.estil

        prompt = f"""Crea especificacions de disseny per a aquesta publicació:

TÍTOL: {request.titol}
AUTOR: {request.autor}
COL·LECCIÓ: {request.colleccio}
ESTIL: {request.estil}
FORMAT: {request.format_principal}
BILINGÜE: {"Sí" if request.bilingue else "No"}

Inclou CSS complet per a EPUB i instruccions per a la portada."""

        return self.process(prompt)

    def generate_css(self, estil: str, bilingue: bool = True) -> AgentResponse:
        """Genera només el CSS per a EPUB.

        Args:
            estil: Estil visual desitjat.
            bilingue: Si és edició bilingüe.

        Returns:
            AgentResponse amb el CSS.
        """
        prompt = f"""Genera CSS complet i professional per a un EPUB de clàssics grecollatins.

ESTIL: {estil}
BILINGÜE: {"Sí, amb text original i traducció" if bilingue else "No, només traducció"}

El CSS ha d'incloure:
- Reset bàsic
- Tipografia del cos
- Estils de títols (h1-h6)
- Paràgrafs i citacions
- Notes a peu de pàgina
- Text en grec i llatí
- {"Classes per a original/traducció" if bilingue else ""}
- Media queries per a diferents dispositius

Retorna NOMÉS el CSS, sense JSON."""

        return self.process(prompt)

    def design_cover(self, titol: str, autor: str, estil: str) -> AgentResponse:
        """Proposa un disseny de portada.

        Args:
            titol: Títol de l'obra.
            autor: Autor.
            estil: Estil visual.

        Returns:
            AgentResponse amb la proposta de portada.
        """
        prompt = f"""Proposa un disseny de portada per:

TÍTOL: {titol}
AUTOR: {autor}
ESTIL: {estil}

Descriu:
- Composició visual
- Colors específics (amb hex)
- Tipografia i disposició del text
- Elements gràfics o il·lustracions suggerides
- Com transmetre l'essència del contingut
- Referents visuals (altres portades similars)"""

        return self.process(prompt)
