"""Agent Pescador de Textos per buscar i descarregar clàssics de domini públic.

Inclou fallback amb Gemini AI per cercar textos a internet quan les fonts
tradicionals no estan disponibles.
"""

import os
import time
from typing import Literal

from pydantic import BaseModel, Field

from agents.base_agent import AgentConfig, AgentResponse, BaseAgent

# Intentar importar Gemini (nou SDK)
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    try:
        # Fallback a SDK antic (deprecated)
        import google.generativeai as genai
        types = None
        GEMINI_AVAILABLE = True
    except ImportError:
        GEMINI_AVAILABLE = False
        genai = None
        types = None


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
    llengua_original: Literal["llatí", "grec", "japonès", "xinès", "anglès", "alemany", "francès", "altres"]
    font: TextSource
    edicio: str | None = None
    any_publicacio: int | None = None
    es_domini_public: bool = True
    notes: str | None = None


class SearchRequest(BaseModel):
    """Sol·licitud de cerca de text."""

    autor: str | None = None
    titol: str | None = None
    llengua: Literal["llatí", "grec", "japonès", "xinès", "anglès", "alemany", "francès", "qualsevol"] = "qualsevol"
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
        return """Ets un expert en biblioteques digitals de textos clàssics universals.

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

5. AOZORA BUNKO (aozora.gr.jp)
   - La millor font per a textos japonesos clàssics i moderns
   - Inclou obres de Meiji, Taisho i principis de Showa
   - Format: HTML o TXT, codificació Shift_JIS (convertir a UTF-8)
   - Autors: Akutagawa, Natsume Soseki, Mori Ogai, etc.

6. CHINESE TEXT PROJECT (ctext.org)
   - Textos clàssics xinesos amb versions paral·leles
   - Confuci, Laozi, poesia Tang i altres

7. CCEL / INTERNET ARCHIVE
   - Textos en anglès, alemany, francès clàssics

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

    def search_with_gemini(
        self,
        autor: str,
        titol: str,
        llengua: str = "francès",
        obtenir_text_complet: bool = True,
    ) -> dict:
        """Cerca un text amb Gemini AI usant Google Search grounding.

        Gemini pot buscar a internet i retornar text de fonts de domini públic.

        Args:
            autor: Nom de l'autor.
            titol: Títol de l'obra.
            llengua: Llengua original del text.
            obtenir_text_complet: Si True, intenta obtenir el text complet.

        Returns:
            Dict amb 'text' (si s'ha trobat), 'font', 'notes'.

        Raises:
            RuntimeError: Si Gemini no està disponible o falla.
        """
        if not GEMINI_AVAILABLE:
            raise RuntimeError(
                "Gemini no està disponible. Instal·la amb: pip install google-generativeai"
            )

        # Configurar Gemini
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Cal configurar GOOGLE_API_KEY o GEMINI_API_KEY per usar Gemini"
            )

        # Crear client Gemini amb el nou SDK
        client = genai.Client(api_key=api_key)

        # Configurar Google Search tool per grounding
        google_search_tool = types.Tool(google_search=types.GoogleSearch())

        start_time = time.time()

        if obtenir_text_complet:
            prompt = f"""Busca el text COMPLET en {llengua} de l'obra "{titol}" de {autor}.

Aquesta obra és de DOMINI PÚBLIC (l'autor va morir fa més de 70 anys).

INSTRUCCIONS:
1. Busca el text original complet a Wikisource, Project Gutenberg, Internet Archive, o altres fonts de domini públic
2. Retorna el TEXT NARRATIU COMPLET de l'obra, no només un resum
3. Inclou TOTS els capítols/seccions de l'obra
4. Indica la font d'on has obtingut el text

FORMAT DE RESPOSTA:
---FONT---
[URL o nom de la font]
---TEXT---
[Text complet de l'obra en {llengua}]
---FI---

IMPORTANT: Necessito el TEXT COMPLET per poder-lo traduir al català. No escurçis ni resumeixis."""
        else:
            prompt = f"""Busca informació sobre on trobar el text complet en {llengua} de "{titol}" de {autor}.

Indica:
1. Les millors fonts de domini públic (Wikisource, Gutenberg, etc.)
2. URLs directes al text
3. Edició recomanada
4. Notes sobre la disponibilitat"""

        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[google_search_tool],
                    temperature=0.2,
                ),
            )
            duration = time.time() - start_time

            text_response = response.text

            # Parsejar resposta
            result = {
                "autor": autor,
                "titol": titol,
                "llengua": llengua,
                "duration_seconds": duration,
            }

            if "---TEXT---" in text_response and "---FI---" in text_response:
                # Extreure text i font
                parts = text_response.split("---TEXT---")
                font_part = parts[0].replace("---FONT---", "").strip()
                text_part = parts[1].split("---FI---")[0].strip()

                result["text"] = text_part
                result["font"] = font_part
                result["success"] = True
            else:
                # Resposta informativa sense text complet
                result["info"] = text_response
                result["success"] = False

            return result

        except Exception as e:
            raise RuntimeError(f"Error en cerca Gemini: {e}") from e

    def obtenir_text_domini_public(
        self,
        autor: str,
        titol: str,
        llengua: str = "francès",
    ) -> str | None:
        """Intenta obtenir un text de domini públic usant múltiples fonts.

        Primer intenta fonts tradicionals (Gutenberg, Wikisource),
        i si fallen, usa Gemini com a fallback.

        Args:
            autor: Nom de l'autor.
            titol: Títol de l'obra.
            llengua: Llengua original.

        Returns:
            Text complet si s'ha trobat, None si no.
        """
        # Primer intentar amb Claude (fonts tradicionals)
        search_result = self.search(
            SearchRequest(
                autor=autor,
                titol=titol,
                llengua=llengua if llengua in ["llatí", "grec", "japonès", "xinès", "anglès", "alemany", "francès"] else "qualsevol",
            )
        )

        # Si Claude ha trobat fonts, retornar la info
        # (caldria implementar descàrrega automàtica)

        # Fallback a Gemini
        if GEMINI_AVAILABLE and (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
            try:
                gemini_result = self.search_with_gemini(
                    autor=autor,
                    titol=titol,
                    llengua=llengua,
                    obtenir_text_complet=True,
                )
                if gemini_result.get("success") and gemini_result.get("text"):
                    return gemini_result["text"]
            except Exception as e:
                self.log_warning(f"Fallback Gemini ha fallat: {e}")

        return None
