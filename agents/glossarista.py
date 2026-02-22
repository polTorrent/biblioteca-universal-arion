"""Agent Glossarista per crear glossaris i índexs."""

import json
import os
from pathlib import Path
from typing import Literal, TYPE_CHECKING

from pydantic import BaseModel, Field

from agents.base_agent import AgentConfig, AgentResponse, BaseAgent

if TYPE_CHECKING:
    from utils.logger import AgentLogger


# Tipus de llengües suportades
SupportedLanguage = Literal["llatí", "grec", "anglès", "alemany", "francès", "japonès", "xinès"]


class GlossaryEntry(BaseModel):
    """Entrada de glossari."""

    terme_original: str
    transliteracio: str | None = None  # Romanització per a japonès/grec
    traduccio_catalana: str
    categoria: str
    definicio: str
    context_us: str | None = None
    termes_relacionats: list[str] = Field(default_factory=list)
    mantenir_original: bool = False  # Si cal mantenir el terme original en cursiva


class OnomasticEntry(BaseModel):
    """Entrada d'índex onomàstic."""

    nom: str
    nom_original: str | None = None  # Kanji, grec, etc.
    variants: list[str] = Field(default_factory=list)
    tipus: Literal["persona", "lloc", "divinitat", "poble", "institució", "era", "obra"]
    descripcio: str
    referencies: list[str] = Field(default_factory=list)


class GlossaryRequest(BaseModel):
    """Sol·licitud de creació de glossari."""

    text: str
    text_original: str | None = None
    llengua_original: SupportedLanguage = "llatí"
    categories: list[str] = Field(default_factory=list)
    genre: str | None = None  # conte, poesia, filosofia, teatre


# Categories per defecte segons llengua
DEFAULT_CATEGORIES: dict[str, list[str]] = {
    "llatí": ["filosofia", "política", "militar", "religió", "vida quotidiana"],
    "grec": ["filosofia", "política", "militar", "religió", "vida quotidiana"],
    "japonès": ["vestimenta", "arquitectura", "rangs", "budisme", "vida quotidiana", "art"],
    "xinès": ["filosofia", "política", "militar", "religió", "vida quotidiana"],
    "anglès": ["filosofia", "política", "vida quotidiana"],
    "alemany": ["filosofia", "política", "vida quotidiana"],
    "francès": ["filosofia", "política", "vida quotidiana"],
}


class GlossaristaAgent(BaseAgent):
    """Agent per crear glossaris terminològics i índexs onomàstics.

    Assegura consistència terminològica i facilita la comprensió
    de termes especialitzats. Suporta llengües clàssiques occidentals
    i orientals.
    """

    agent_name: str = "Glossarista"

    # Prompt específic per a japonès
    _JAPANESE_PROMPT = '''Ets un lexicògraf expert en terminologia japonesa clàssica i moderna.

OBJECTIU:
Crear glossaris complets i índexs onomàstics per a edicions de textos japonesos en català.

TIPUS D'ENTRADES:

1. VESTIMENTA (mantenir en japonès + explicació)
   - Roba formal: kariginu, hakama, hitatare, sokutai
   - Roba femenina: uchigi, akome, karaginu, junihitoe
   - Complements: eboshi, tabi, obi, geta, zori
   - Criteris: primera aparició amb explicació, després només en cursiva

2. ARQUITECTURA (mantenir en japonès + explicació)
   - Elements: fusuma, shoji, tatami, tokonoma, engawa
   - Habitacions: zashiki, ima, doma
   - Estructures: torii, pagoda, shiro

3. RANGS I TÍTOLS
   - Cort imperial: tenno, kogo, naishinnō
   - Noblesa: kuge, daimyo, samurai
   - Sufixos: -sama, -dono, -san, -kun, -chan
   - Criteris: adaptar al context (Gran Senyor, Senyora, etc.)

4. RELIGIÓ I FILOSOFIA
   - Budisme: karma, samsara, naraka, bodhi, sutra
   - Xintoisme: kami, miko, kannushi, shimenawa
   - Conceptes: mono no aware, wabi-sabi, yugen, ma

5. ÈPOQUES I PERÍODES
   - Heian (794-1185), Kamakura (1185-1333)
   - Muromachi (1336-1573), Edo (1603-1868)
   - Meiji (1868-1912), Taisho (1912-1926)

6. NOMS PROPIS
   - Ordre: cognom + nom (Akutagawa Ryunosuke)
   - Romanització: Hepburn modificat
   - Llocs: nom japonès + localització moderna si cal

CRITERIS DE ROMANITZACIÓ (Hepburn modificat):
- shi (no si), tsu, chi, fu
- wo esdevé o, ha esdevé wa (partícules)
- Vocals llargues: usar macrons (o, u)
- N abans de b/m/p: es manté com n (shinbun, no shimbun)

FORMAT DE RESPOSTA JSON:
{
    "glossari": [
        {
            "terme_original": "<terme en kanji>",
            "transliteracio": "<romanització Hepburn>",
            "traduccio_catalana": "<traducció o mantenir original>",
            "categoria": "<vestimenta|arquitectura|rangs|budisme|xintoisme|vida quotidiana|art>",
            "definicio": "<definició clara i concisa>",
            "context_us": "<com s'usa en aquest text>",
            "termes_relacionats": ["<terme>"],
            "mantenir_original": true o false,
            "nota": "<observacions si cal>"
        }
    ],
    "index_onomastic": [
        {
            "nom": "<nom romanitzat>",
            "nom_original": "<kanji si disponible>",
            "variants": ["<altres lectures>"],
            "tipus": "<persona|lloc|divinitat|era|obra|institució>",
            "descripcio": "<qui o què és>",
            "referencies": ["<on apareix al text>"]
        }
    ],
    "estadistiques": {
        "total_termes": <número>,
        "total_noms": <número>,
        "categories": {"<categoria>": <número>},
        "termes_a_mantenir": <número>
    },
    "recomanacions_traductor": [
        "<consell per mantenir consistència>",
        "<notes sobre registre o to>"
    ]
}'''

    _DEFAULT_PROMPT = '''Ets un lexicògraf expert en terminologia clàssica grecollatina.

OBJECTIU:
Crear glossaris complets i índexs onomàstics per a edicions de textos clàssics en català.

TIPUS D'ENTRADES:

1. TERMES TÈCNICS
   - Filosofia: logos, physis, eudaimonia, virtus, ratio...
   - Política: polis, res publica, senatus, demos, civitas...
   - Militar: legió, falange, cohors, strategos...
   - Religió: numen, pietas, sacerdos, theos, hiereus...
   - Retòrica: ethos, pathos, logos, enthymema...

2. CONCEPTES CULTURALS
   - Institucions: magistratures, assemblees, tribunals
   - Costums: banquets, jocs, rituals
   - Mesures: estadi, talent, as, sesterci
   - Calendari: calendes, nones, idus

3. NOMS PROPIS
   - Persones: forma catalana tradicional si existeix
   - Llocs: nom antic i equivalent modern
   - Pobles: gentilicis i localització
   - Divinitats: nom grec/llatí i atributs

CRITERIS DE TRADUCCIÓ TERMINOLÒGICA:
- Preferir traduccions catalanes tradicionals si existeixen
- Mantenir el terme original entre parèntesis si és molt específic
- Ser consistent: un terme = una traducció
- Indicar si hi ha debat terminològic

FORMAT DE RESPOSTA JSON:
{
    "glossari": [
        {
            "terme_original": "<terme en grec/llatí>",
            "transliteracio": "<si és grec>",
            "traduccio_catalana": "<traducció recomanada>",
            "categoria": "<filosofia|política|militar|religió|retòrica|altre>",
            "definicio": "<definició clara i concisa>",
            "context_us": "<com s'usa en aquest text>",
            "termes_relacionats": ["<terme>"],
            "nota": "<observacions si cal>"
        }
    ],
    "index_onomastic": [
        {
            "nom": "<nom principal>",
            "variants": ["<altres formes>"],
            "tipus": "<persona|lloc|divinitat|poble|institució>",
            "descripcio": "<qui o què és>",
            "referencies": ["<on apareix al text>"]
        }
    ],
    "estadistiques": {
        "total_termes": <número>,
        "total_noms": <número>,
        "categories": {"<categoria>": <número>}
    },
    "recomanacions_traductor": [
        "<consell per mantenir consistència>"
    ]
}'''

    def __init__(
        self,
        config: AgentConfig | None = None,
        logger: "AgentLogger | None" = None,
        llengua: SupportedLanguage = "llatí",
    ) -> None:
        super().__init__(config, logger)
        self.llengua = llengua
        self.cache_path = Path.home() / ".openclaw" / "workspace" / "biblioteca-universal-arion" / "output" / ".cache" / "cache_glossari.json"
        self._inicialitzar_cache()

    def _inicialitzar_cache(self) -> None:
        """Inicialitza l'arxiu de caché si no existeix."""
        if not self.cache_path.parent.exists():
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            
        if not self.cache_path.exists():
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)

    def _carregar_cache(self) -> dict:
        """Carrega el glossari de la caché."""
        try:
            with open(self.cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _guardar_a_cache(self, nous_termes_glossari: list[dict], llengua: str) -> None:
        """Desa els nous termes al diccionari de caché per llengua."""
        cache = self._carregar_cache()
        if llengua not in cache:
            cache[llengua] = {}
            
        for terme in nous_termes_glossari:
            original = terme.get("terme_original")
            if original:
                cache[llengua][original] = terme
                
        with open(self.cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)

    @property
    def system_prompt(self) -> str:
        if self.llengua == "japonès":
            return self._JAPANESE_PROMPT
        return self._DEFAULT_PROMPT

    def create_glossary(self, request: GlossaryRequest) -> AgentResponse:
        """Crea un glossari per a un text usant caché per termes coneguts.

        Args:
            request: Sol·licitud amb el text i categories.

        Returns:
            AgentResponse amb el glossari complet.
        """
        # Actualitzar la llengua de l'agent
        self.llengua = request.llengua_original
        cache = self._carregar_cache()
        llengua_cache = cache.get(self.llengua, {})

        # Usar categories per defecte si no s'especifiquen
        categories = request.categories
        if not categories:
            categories = DEFAULT_CATEGORIES.get(
                request.llengua_original,
                ["filosofia", "política", "religió", "vida quotidiana"]
            )

        prompt_parts = [
            "Crea un glossari complet per a aquest text.",
            f"Llengua original: {request.llengua_original}",
            f"Categories a incloure: {', '.join(categories)}",
        ]
        
        # Injectar termes prèviament coneguts (caché) perquè el LLM els utilitzi i conservi coherència
        if llengua_cache:
            prompt_parts.append("\nTERMES CONEGUTS (Usa aquestes traduccions prèviament validades si apareixen en el text):")
            for term, dades in llengua_cache.items():
                prompt_parts.append(f"- {term}: {dades.get('traduccio_catalana', '')} ({dades.get('definicio', '')})")

        if request.genre:
            prompt_parts.append(f"\nGènere: {request.genre}")

        prompt_parts.extend([
            "",
            "TEXT TRADUÏT:",
            request.text[:4000] + "..." if len(request.text) > 4000 else request.text,
        ])

        if request.text_original:
            prompt_parts.extend([
                "",
                "TEXT ORIGINAL:",
                request.text_original[:2000] + "..." if len(request.text_original) > 2000 else request.text_original,
            ])

        resposta_llm = self.process("\n".join(prompt_parts))
        
        # Parsejar el resultat per extraure i guardar termes nous
        try:
            resultat_json = json.loads(resposta_llm.content)
            # Extracció i desat a la caché per posteriors invocacions
            glossaris_generats = resultat_json.get("glossari", [])
            if glossaris_generats:
                self._guardar_a_cache(glossaris_generats, self.llengua)
        except Exception:
            pass  # ignorant si el LLM no retorna JSON vàlid pur i té markdown o text de més

        return resposta_llm

    def propose_translation(self, terme: str, context: str) -> AgentResponse:
        """Proposa una traducció per a un terme difícil.

        Args:
            terme: Terme a traduir.
            context: Context d'ús.

        Returns:
            AgentResponse amb les opcions de traducció.
        """
        prompt = f"""Proposa traduccions al català per al terme: {terme}

CONTEXT D'ÚS:
{context}

Retorna JSON amb:
- opcions: [{{"traduccio": "...", "justificacio": "...", "adequacio": 1-10}}]
- recomanacio: <millor opció>
- termes_a_evitar: [<falsos amics>]"""

        return self.process(prompt)

    def check_consistency(self, glossari: dict, text: str) -> AgentResponse:
        """Verifica la consistència terminològica d'un text.

        Args:
            glossari: Glossari de referència.
            text: Text a verificar.

        Returns:
            AgentResponse amb les inconsistències detectades.
        """
        prompt = f"""Verifica que aquest text segueix el glossari de manera consistent.

GLOSSARI:
{json.dumps(glossari, ensure_ascii=False, indent=2)[:2000]}

TEXT:
{text[:3000]}

Identifica:
- Termes traduïts de manera inconsistent
- Termes que falten al glossari
- Usos incorrectes segons el glossari"""

        return self.process(prompt)
