"""Agent Pescador de Textos per buscar i descarregar clàssics de domini públic."""

from typing import Literal

from pydantic import BaseModel, Field

from agents.base_agent import AgentConfig, AgentResponse, BaseAgent


class TextSource(BaseModel):
    """Font d'un text clàssic."""

    nom: str
    url: str
    tipus: Literal["perseus", "latin_library", "gutenberg", "wikisource", "altre"]
    llicencia: str = "domini públic"


class TextMetadata(BaseModel):
    """Metadades d'un text descarregat."""

    titol: str
    autor: str
    llengua_original: Literal["llatí", "grec", "altres"]
    font: TextSource
    edicio: str | None = None
    any_publicacio: int | None = None
    es_domini_public: bool = True
    notes: str | None = None


class SearchRequest(BaseModel):
    """Sol·licitud de cerca de text."""

    autor: str | None = None
    titol: str | None = None
    llengua: Literal["llatí", "grec", "qualsevol"] = "qualsevol"
    preferencies_font: list[str] = Field(default_factory=lambda: ["perseus", "latin_library"])


class PescadorTextosAgent(BaseAgent):
    """Agent per buscar i obtenir textos clàssics de domini públic.

    Cerca a biblioteques digitals com Perseus, The Latin Library,
    Project Gutenberg i Wikisource.
    """

    def __init__(self, config: AgentConfig | None = None) -> None:
        super().__init__(config)

    @property
    def system_prompt(self) -> str:
        return """Ets un expert en biblioteques digitals de textos clàssics grecollatins.

OBJECTIU:
Ajudar a localitzar, identificar i obtenir textos clàssics de domini públic en les millors edicions disponibles.

FONTS PRINCIPALS:

1. PERSEUS DIGITAL LIBRARY (perseus.tufts.edu)
   - La millor font per a textos grecs i llatins
   - Inclou aparats crítics i traduccions
   - Format TEI/XML, molt estructurat
   - URL patró: perseus.tufts.edu/hopper/text?doc=Perseus:text:...

2. THE LATIN LIBRARY (thelatinlibrary.com)
   - Excel·lent col·lecció de textos llatins
   - Text pla, fàcil de processar
   - Organitzat per autor

3. PROJECT GUTENBERG (gutenberg.org)
   - Textos complets, sovint amb traducció anglesa
   - Format TXT o HTML
   - Verificar que sigui l'original, no només traducció

4. WIKISOURCE (la.wikisource.org, el.wikisource.org)
   - Textos llatins i grecs col·laboratius
   - Qualitat variable, verificar edició

CRITERIS DE SELECCIÓ:
- Preferir edicions crítiques (Teubner, OCT, Loeb)
- Verificar que el text és complet
- Comprovar domini públic (autor mort >70 anys, edició >95 anys)
- Preferir textos amb numeració estàndard (llibres, capítols, versos)

FORMAT DE RESPOSTA:
Respon en JSON amb aquesta estructura:
{
    "resultats": [
        {
            "titol": "<títol de l'obra>",
            "autor": "<nom de l'autor>",
            "llengua": "<llatí|grec>",
            "font": {
                "nom": "<nom de la biblioteca>",
                "url": "<URL directa al text>",
                "tipus": "<perseus|latin_library|gutenberg|wikisource>"
            },
            "edicio": "<nom de l'edició si es coneix>",
            "qualitat": <1-10>,
            "notes": "<observacions sobre aquesta versió>"
        }
    ],
    "recomanacio": "<quin resultat es recomana i per què>",
    "instruccions_descarrega": "<com obtenir el text net>"
}"""

    def search(self, request: SearchRequest) -> AgentResponse:
        """Cerca textos segons els criteris especificats.

        Args:
            request: Criteris de cerca.

        Returns:
            AgentResponse amb els resultats de la cerca.
        """
        prompt_parts = ["Cerca textos clàssics amb aquests criteris:"]

        if request.autor:
            prompt_parts.append(f"- Autor: {request.autor}")
        if request.titol:
            prompt_parts.append(f"- Títol: {request.titol}")
        if request.llengua != "qualsevol":
            prompt_parts.append(f"- Llengua: {request.llengua}")

        prompt_parts.append(f"- Fonts preferides: {', '.join(request.preferencies_font)}")
        prompt_parts.append("\nRetorna les millors opcions disponibles.")

        return self.process("\n".join(prompt_parts))

    def verify_public_domain(self, autor: str, any_mort: int | None = None) -> AgentResponse:
        """Verifica si una obra és de domini públic.

        Args:
            autor: Nom de l'autor.
            any_mort: Any de mort de l'autor si es coneix.

        Returns:
            AgentResponse amb l'anàlisi de domini públic.
        """
        prompt = f"""Verifica si les obres de {autor} són de domini públic.
{"Any de mort: " + str(any_mort) if any_mort else ""}

Considera:
1. Drets d'autor de l'obra original
2. Drets de les edicions modernes
3. Legislació europea (70 anys post mortem)

Retorna JSON amb: es_domini_public (bool), explicacio, precaucions."""

        return self.process(prompt)

    def extract_clean_text(self, url: str, format_origen: str) -> AgentResponse:
        """Genera instruccions per netejar un text descarregat.

        Args:
            url: URL del text.
            format_origen: Format del text (html, xml, txt).

        Returns:
            AgentResponse amb instruccions de neteja.
        """
        prompt = f"""Dóna instruccions per extreure text net de:
URL: {url}
Format: {format_origen}

Inclou:
1. Com descarregar el contingut
2. Com eliminar HTML/XML i metadades
3. Com preservar l'estructura (llibres, capítols)
4. Com codificar correctament els caràcters grecs/llatins"""

        return self.process(prompt)
