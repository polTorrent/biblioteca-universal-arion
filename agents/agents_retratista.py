"""Agent per a la generació de retrats d'autors amb estil Neo-Clàssic Digital.

Utilitza Claude per crear prompts artístics i Venice.ai per generar imatges.
Estil visual: Bust de marbre clàssic amb subtils elements digitals.
Format: Quadrat 1:1 per avatars, o 3:4 per fitxes.

Exemple d'ús:
    ```python
    from agents.retratista import AgentRetratista, generar_retrat_autor
    
    # Ús ràpid
    retrat = generar_retrat_autor(
        nom="Plató",
        epoca="Grècia clàssica, s. V-IV aC",
        genere="FIL",
        output_path="autors/plato.png",
    )
    
    # Ús amb agent
    agent = AgentRetratista()
    retrat = agent.generar_retrat({
        "nom": "Homer",
        "epoca": "Grècia arcaica, s. VIII aC",
        "genere": "EPO",
        "descripcio": "Poeta cec llegendari",
    })
    ```
"""

import io
import json
import os
from pathlib import Path
from typing import Literal

from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, Field

# Imports relatius per quan s'integri al projecte
try:
    from agents.base_agent import AgentConfig, AgentResponse, BaseAgent
    from agents.venice_client import VeniceClient, VeniceError
except ImportError:
    # Stubs per desenvolupament independent
    from abc import ABC, abstractmethod
    
    class AgentConfig(BaseModel):
        model: str = "claude-sonnet-4-20250514"
        max_tokens: int = 2048
        temperature: float = 0.7
    
    class AgentResponse(BaseModel):
        content: str
        model: str = ""
        usage: dict = {}
        duration_seconds: float = 0.0
        cost_eur: float = 0.0
    
    class BaseAgent(ABC):
        agent_name: str = "BaseAgent"
        
        def __init__(self, config: AgentConfig | None = None):
            self.config = config or AgentConfig()
            self._logger = None
        
        @property
        @abstractmethod
        def system_prompt(self) -> str:
            ...
        
        def log_info(self, msg: str) -> None:
            print(f"ℹ️  {msg}")
        
        def log_error(self, msg: str) -> None:
            print(f"❌ {msg}")
        
        def process(self, prompt: str) -> AgentResponse:
            # Placeholder - en producció usa Claude
            return AgentResponse(content="{}")
    
    class VeniceClient:
        def __init__(self, api_key: str | None = None):
            self.api_key = api_key or os.getenv("VENICE_API_KEY")
        
        def generar_imatge_sync(self, **kwargs) -> bytes:
            raise NotImplementedError("Venice client stub")
    
    class VeniceError(Exception):
        pass


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓ D'ESTILS PER GÈNERE
# ═══════════════════════════════════════════════════════════════════════════

GenreLiterari = Literal["FIL", "POE", "TEA", "NOV", "SAG", "ORI", "EPO", "HIS", "CIE"]


class EstilRetrat(BaseModel):
    """Configuració d'estil per a un gènere literari."""
    
    marbre: str  # Tipus de marbre
    il_luminacio: str  # Estil d'il·luminació
    accent_digital: str  # Element digital subtil
    accent_color: str  # Color d'accent (hex)
    fons: str  # Descripció del fons
    expressio: str  # Expressió facial
    detalls: str  # Detalls addicionals


ESTILS_GENERE: dict[str, EstilRetrat] = {
    "FIL": EstilRetrat(
        marbre="pure white Carrara marble",
        il_luminacio="dramatic side lighting from left, chiaroscuro",
        accent_digital="subtle golden geometric shapes floating nearby, thin horizontal scan lines",
        accent_color="#D4AF37",
        fons="dark gradient background from charcoal (#36454F) to black",
        expressio="serene contemplative expression, wise gaze",
        detalls="classical Greek beard, noble brow",
    ),
    "POE": EstilRetrat(
        marbre="soft cream Parian marble with subtle pink veins",
        il_luminacio="ethereal soft lighting, gentle shadows",
        accent_digital="delicate floating particles like stardust, faint digital aurora",
        accent_color="#B8A9C9",
        fons="deep indigo gradient fading to black",
        expressio="dreamy introspective expression, eyes slightly upward",
        detalls="flowing hair suggested in marble, refined features",
    ),
    "TEA": EstilRetrat(
        marbre="dramatic white marble with bold shadows",
        il_luminacio="theatrical spotlight from above, high contrast",
        accent_digital="crimson light fragments at edges, subtle stage light flares",
        accent_color="#8B0000",
        fons="pure black void, dramatic emptiness",
        expressio="intense passionate expression, theatrical gravitas",
        detalls="expressive features, strong jaw line",
    ),
    "NOV": EstilRetrat(
        marbre="warm ivory marble, slightly weathered",
        il_luminacio="natural diffused light, storyteller's warmth",
        accent_digital="sepia-toned digital grain, vintage scan artifacts",
        accent_color="#8B7355",
        fons="rich brown gradient suggesting old parchment",
        expressio="knowing half-smile, observant eyes",
        detalls="character lines suggesting life experience",
    ),
    "SAG": EstilRetrat(
        marbre="luminous white marble with ethereal glow",
        il_luminacio="divine light from above, halo effect",
        accent_digital="golden sacred geometry patterns, subtle mandala fragments",
        accent_color="#FFD700",
        fons="deep celestial blue transitioning to cosmic black",
        expressio="transcendent peaceful expression, inner light",
        detalls="serene features, slight upward gaze",
    ),
    "ORI": EstilRetrat(
        marbre="pale grey-white marble, zen simplicity",
        il_luminacio="soft balanced light, no harsh shadows",
        accent_digital="single red ink brushstroke accent, minimal interference",
        accent_color="#8B0000",
        fons="misty gradient from warm grey to soft white",
        expressio="profound stillness, enigmatic calm",
        detalls="simplified features, suggestion of Asian influence if appropriate",
    ),
    "EPO": EstilRetrat(
        marbre="ancient weathered marble, heroic presence",
        il_luminacio="epic golden hour lighting, mythic atmosphere",
        accent_digital="bronze-gold digital particles, ancient patina effect",
        accent_color="#CD853F",
        fons="stormy gradient suggesting Aegean skies",
        expressio="heroic determination, far-seeing gaze",
        detalls="strong classical features, possibly blind eyes for Homer",
    ),
    "HIS": EstilRetrat(
        marbre="dignified grey-veined marble",
        il_luminacio="scholarly lamplight, warm and focused",
        accent_digital="faint text fragments floating, document scan lines",
        accent_color="#4A5568",
        fons="deep library green to black gradient",
        expressio="analytical scrutiny, intellectual intensity",
        detalls="prominent brow, scholarly bearing",
    ),
    "CIE": EstilRetrat(
        marbre="cool blue-white marble, precision carved",
        il_luminacio="clean clinical light, revealing detail",
        accent_digital="geometric grid overlay, measurement marks",
        accent_color="#4682B4",
        fons="deep space blue to black, suggesting cosmos",
        expressio="curious wonder, analytical focus",
        detalls="alert eyes, inquiring posture",
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓ DE L'AGENT
# ═══════════════════════════════════════════════════════════════════════════

class RetratistaConfig(BaseModel):
    """Configuració de l'agent retratista."""
    
    width: int = Field(default=1024, ge=512, le=1280)
    height: int = Field(default=1024, ge=512, le=1280)
    format_ratio: Literal["1:1", "3:4"] = "1:1"
    model_imatge: str = "flux-2-max"
    steps: int = Field(default=35, ge=20, le=50)
    cfg_scale: float = Field(default=7.5, ge=5.0, le=12.0)
    afegir_marc: bool = False
    afegir_nom: bool = False


class PromptResult(BaseModel):
    """Resultat de la generació de prompt."""
    
    prompt: str
    negative_prompt: str
    estil: dict
    raonament: str


# ═══════════════════════════════════════════════════════════════════════════
# AGENT RETRATISTA
# ═══════════════════════════════════════════════════════════════════════════

class AgentRetratista(BaseAgent):
    """Agent per generar retrats d'autors amb estil Neo-Clàssic Digital.
    
    Combina l'estètica dels bustos clàssics de marbre amb subtils
    elements digitals contemporanis, creant una fusió entre l'antic i el modern.
    """
    
    agent_name: str = "Retratista"
    
    def __init__(
        self,
        config: AgentConfig | None = None,
        retratista_config: RetratistaConfig | None = None,
    ) -> None:
        """Inicialitza l'agent retratista.
        
        Args:
            config: Configuració de l'agent base (Claude).
            retratista_config: Configuració específica per retrats.
        """
        super().__init__(config)
        self.retratista_config = retratista_config or RetratistaConfig()
        
        # Ajustar dimensions segons format
        if self.retratista_config.format_ratio == "3:4":
            self.retratista_config.width = 1024
            self.retratista_config.height = 1280
        
        # Inicialitzar client Venice
        try:
            self.venice = VeniceClient()
            self.log_info("Client Venice inicialitzat correctament")
        except Exception as e:
            self.venice = None
            self.log_error(f"Venice no disponible: {e}")
    
    @property
    def system_prompt(self) -> str:
        return """Ets un expert en iconografia clàssica i art digital contemporani.

La teva tasca és crear prompts per generar retrats d'autors clàssics amb l'estil
"Neo-Clàssic Digital": bustos de marbre amb subtils elements digitals.

PRINCIPIS DE L'ESTIL NEO-CLÀSSIC DIGITAL:

1. BASE CLÀSSICA (70% de l'impacte visual)
   - Bust de marbre blanc/crema estil hel·lenístic o romà
   - Talla detallada amb textura de marbre realista
   - Il·luminació dramàtica tipus museu
   - Expressió que reflecteixi l'esperit de l'autor

2. ELEMENTS DIGITALS (30% de l'impacte visual)
   - SUBTILS, mai dominants
   - Línies d'escaneig horitzontals molt fines
   - Petits glitchs als contorns (opcionals)
   - Geometria daurada flotant a prop (no tocant)
   - Partícules de llum digital

3. COMPOSICIÓ
   - Fons fosc amb gradient (no blanc mai)
   - Bust centrat, des del pit fins sobre el cap
   - Espai negatiu respectat
   - Format retratat clàssic

EVITAR SEMPRE:
- Estètica cyberpunk o massa futurista
- Colors brillants o neó
- Text o lletres
- Cossos complets o mans
- Fons blancs o clars
- Estil cartoon o anime
- Elements moderns (roba actual, tecnologia visible)

FORMAT DE RESPOSTA (JSON):
{
    "prompt": "descripció completa per Venice/FLUX",
    "negative_prompt": "elements a evitar",
    "raonament": "per què aquest enfocament per a aquest autor"
}"""
    
    def _obtenir_estil(self, genere: str) -> EstilRetrat:
        """Obté l'estil per un gènere, amb fallback a FIL."""
        return ESTILS_GENERE.get(genere.upper(), ESTILS_GENERE["FIL"])
    
    def _construir_prompt_base(
        self,
        nom: str,
        epoca: str,
        genere: str,
        descripcio: str = "",
    ) -> str:
        """Construeix el prompt base sense usar Claude."""
        estil = self._obtenir_estil(genere)
        
        prompt_parts = [
            f"Portrait bust sculpture of {nom}",
            f"ancient {epoca} figure",
            f"{estil.marbre} sculpture style",
            "classical Hellenistic period aesthetic",
            f"{estil.il_luminacio}",
            f"{estil.accent_digital}",
            f"{estil.fons}",
            f"{estil.expressio}",
            f"{estil.detalls}",
            "hyper-detailed marble texture with subtle veins",
            "museum quality sculpture photography",
            "8k resolution",
            "photorealistic marble rendering",
        ]
        
        if descripcio:
            prompt_parts.insert(2, descripcio)
        
        return ", ".join(prompt_parts)
    
    def _construir_negative_prompt(self) -> str:
        """Construeix el negative prompt estàndard."""
        return (
            "cartoon, anime, illustration, painting, drawing, sketch, "
            "colorful, vibrant colors, neon, cyberpunk, futuristic, "
            "modern clothing, contemporary, text, letters, watermark, signature, "
            "low quality, blurry, distorted face, deformed, "
            "full body, hands, fingers, multiple people, "
            "bright background, white background, plain background, "
            "excessive glitch, too digital, heavy artifacts, "
            "realistic human skin, photograph of person, "
            "3d render plastic, wax figure"
        )
    
    def generar_prompt(self, metadata: dict) -> dict:
        """Genera el prompt per a un retrat d'autor.
        
        Args:
            metadata: Diccionari amb:
                - nom: Nom de l'autor (obligatori)
                - epoca: Època/context històric (obligatori)
                - genere: Gènere literari (FIL, POE, etc.)
                - descripcio: Descripció adicional (opcional)
                - trets: Característiques físiques conegudes (opcional)
        
        Returns:
            Diccionari amb prompt, negative_prompt, estil i raonament.
        """
        nom = metadata.get("nom", "Unknown Author")
        epoca = metadata.get("epoca", "ancient classical period")
        genere = metadata.get("genere", "FIL")
        descripcio = metadata.get("descripcio", "")
        trets = metadata.get("trets", "")
        
        # Combinar descripció i trets si existeixen
        desc_completa = " ".join(filter(None, [descripcio, trets]))
        
        estil = self._obtenir_estil(genere)
        
        prompt = self._construir_prompt_base(nom, epoca, genere, desc_completa)
        negative = self._construir_negative_prompt()
        
        return {
            "prompt": prompt,
            "negative_prompt": negative,
            "estil": estil.model_dump(),
            "genere": genere,
            "raonament": f"Estil {genere} aplicat a {nom}: {estil.expressio}",
        }
    
    def generar_retrat(
        self,
        metadata: dict,
        usar_claude: bool = False,
    ) -> bytes:
        """Genera un retrat complet d'autor.
        
        Args:
            metadata: Metadades de l'autor (nom, epoca, genere, etc.)
            usar_claude: Si True, usa Claude per refinar el prompt.
        
        Returns:
            bytes: Imatge PNG del retrat.
        
        Raises:
            VeniceError: Si falla la generació d'imatge.
            ValueError: Si Venice no està disponible.
        """
        if not self.venice:
            raise ValueError(
                "Client Venice no disponible. "
                "Configura VENICE_API_KEY a l'entorn."
            )
        
        # 1. Generar prompt
        self.log_info(f"Generant prompt per: {metadata.get('nom', 'desconegut')}")
        prompt_result = self.generar_prompt(metadata)
        
        # 2. Opcional: Refinar amb Claude
        if usar_claude:
            self.log_info("Refinant prompt amb Claude...")
            # Aquí es podria cridar self.process() per refinar
            pass
        
        # 3. Generar imatge amb Venice
        self.log_info("Generant imatge amb Venice.ai...")
        image_bytes = self.venice.generar_imatge_sync(
            prompt=prompt_result["prompt"],
            negative_prompt=prompt_result["negative_prompt"],
            width=self.retratista_config.width,
            height=self.retratista_config.height,
            model=self.retratista_config.model_imatge,
            steps=self.retratista_config.steps,
            cfg_scale=self.retratista_config.cfg_scale,
        )
        
        self.log_info("Retrat generat correctament!")
        return image_bytes
    
    def generar_i_guardar(
        self,
        metadata: dict,
        output_dir: Path | str = "output/autors",
    ) -> Path:
        """Genera un retrat i el guarda a disc.
        
        Args:
            metadata: Metadades de l'autor.
            output_dir: Directori de sortida.
        
        Returns:
            Path al fitxer generat.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Nom de fitxer segur
        nom = metadata.get("nom", "autor_desconegut")
        nom_segur = nom.lower().replace(" ", "_").replace("'", "")
        for char in "àèéíòóúïüç":
            repl = {"à": "a", "è": "e", "é": "e", "í": "i", "ò": "o", 
                    "ó": "o", "ú": "u", "ï": "i", "ü": "u", "ç": "c"}
            nom_segur = nom_segur.replace(char, repl.get(char, char))
        
        output_path = output_dir / f"{nom_segur}.png"
        
        # Generar i guardar
        image_bytes = self.generar_retrat(metadata)
        output_path.write_bytes(image_bytes)
        
        self.log_info(f"Retrat guardat: {output_path}")
        return output_path


# ═══════════════════════════════════════════════════════════════════════════
# FUNCIONS D'AJUDA
# ═══════════════════════════════════════════════════════════════════════════

def generar_retrat_autor(
    nom: str,
    epoca: str,
    genere: str = "FIL",
    descripcio: str = "",
    trets: str = "",
    output_path: Path | str | None = None,
) -> bytes:
    """Funció ràpida per generar un retrat d'autor.
    
    Args:
        nom: Nom de l'autor.
        epoca: Època històrica.
        genere: Gènere literari (FIL, POE, TEA, NOV, SAG, ORI, EPO, HIS, CIE).
        descripcio: Descripció adicional.
        trets: Característiques físiques conegudes.
        output_path: Ruta on guardar la imatge (opcional).
    
    Returns:
        bytes: Imatge PNG del retrat.
    
    Exemple:
        ```python
        retrat = generar_retrat_autor(
            nom="Marc Aureli",
            epoca="Roma Imperial, s. II dC",
            genere="FIL",
            descripcio="Emperador filòsof estoic",
            output_path="autors/marc_aureli.png",
        )
        ```
    """
    agent = AgentRetratista()
    
    metadata = {
        "nom": nom,
        "epoca": epoca,
        "genere": genere,
        "descripcio": descripcio,
        "trets": trets,
    }
    
    image_bytes = agent.generar_retrat(metadata)
    
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(image_bytes)
        print(f"✅ Retrat guardat: {path}")
    
    return image_bytes


def previsualitzar_prompt(
    nom: str,
    epoca: str,
    genere: str = "FIL",
    descripcio: str = "",
) -> dict:
    """Previsualitza el prompt sense generar imatge.
    
    Útil per revisar el prompt abans de gastar crèdits de Venice.
    
    Returns:
        dict amb prompt, negative_prompt, estil i raonament.
    """
    agent = AgentRetratista()
    return agent.generar_prompt({
        "nom": nom,
        "epoca": epoca,
        "genere": genere,
        "descripcio": descripcio,
    })


# ═══════════════════════════════════════════════════════════════════════════
# AUTORS PREDEFINITS (per comoditat)
# ═══════════════════════════════════════════════════════════════════════════

AUTORS_CLASSICS = {
    "plato": {
        "nom": "Plató",
        "epoca": "Grècia clàssica, s. V-IV aC",
        "genere": "FIL",
        "descripcio": "Filòsof atenès, deixeble de Sòcrates",
        "trets": "barba grega clàssica, front ample, nas recte",
    },
    "aristotil": {
        "nom": "Aristòtil",
        "epoca": "Grècia clàssica, s. IV aC",
        "genere": "FIL",
        "descripcio": "Filòsof i científic, deixeble de Plató",
        "trets": "barba curta i ben retallada, mirada penetrant",
    },
    "homer": {
        "nom": "Homer",
        "epoca": "Grècia arcaica, s. VIII aC",
        "genere": "EPO",
        "descripcio": "Poeta èpic llegendari, autor de la Ilíada i l'Odissea",
        "trets": "ancià cec amb ulls tancats o buits, barba llarga fluent",
    },
    "safo": {
        "nom": "Safo",
        "epoca": "Grècia arcaica, s. VII-VI aC",
        "genere": "POE",
        "descripcio": "Poetessa de Lesbos, la desena musa",
        "trets": "faccions femenines delicades, cabell recollit estil grec",
    },
    "sofocles": {
        "nom": "Sòfocles",
        "epoca": "Grècia clàssica, s. V aC",
        "genere": "TEA",
        "descripcio": "Dramaturg tràgic atenès",
        "trets": "barba digna, expressió tràgica noble",
    },
    "marc_aureli": {
        "nom": "Marc Aureli",
        "epoca": "Roma Imperial, s. II dC",
        "genere": "FIL",
        "descripcio": "Emperador filòsof estoic",
        "trets": "barba rissada romana, corona de llorer suggerida",
    },
    "seneca": {
        "nom": "Sèneca",
        "epoca": "Roma Imperial, s. I dC",
        "genere": "FIL",
        "descripcio": "Filòsof estoic i dramaturg",
        "trets": "calb o amb poc cabell, expressió severa però sàvia",
    },
    "virgili": {
        "nom": "Virgili",
        "epoca": "Roma Augusta, s. I aC",
        "genere": "EPO",
        "descripcio": "Poeta de l'Eneida",
        "trets": "faccions fines, expressió melancòlica",
    },
    "ovidi": {
        "nom": "Ovidi",
        "epoca": "Roma Augusta, s. I aC - I dC",
        "genere": "POE",
        "descripcio": "Poeta de les Metamorfosis",
        "trets": "rostre juvenil, somriure subtil",
    },
    "herodot": {
        "nom": "Heròdot",
        "epoca": "Grècia clàssica, s. V aC",
        "genere": "HIS",
        "descripcio": "Pare de la història",
        "trets": "barba plena, mirada curiosa i observadora",
    },
}


def generar_autor_classic(clau: str, output_dir: str = "output/autors") -> Path:
    """Genera retrat d'un autor predefinit.
    
    Args:
        clau: Clau de l'autor (plato, homer, etc.)
        output_dir: Directori de sortida.
    
    Returns:
        Path al fitxer generat.
    
    Exemple:
        ```python
        generar_autor_classic("plato")
        generar_autor_classic("homer", "web/img/autors")
        ```
    """
    if clau not in AUTORS_CLASSICS:
        claus_disponibles = ", ".join(AUTORS_CLASSICS.keys())
        raise ValueError(f"Autor '{clau}' no trobat. Disponibles: {claus_disponibles}")
    
    agent = AgentRetratista()
    return agent.generar_i_guardar(AUTORS_CLASSICS[clau], output_dir)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN / TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("AGENT RETRATISTA - Neo-Clàssic Digital")
    print("=" * 60)
    
    agent = AgentRetratista()
    print(f"✅ Agent creat")
    print(f"   Venice: {'✅ Disponible' if agent.venice else '❌ No disponible'}")
    print(f"   Format: {agent.retratista_config.width}x{agent.retratista_config.height}")
    print()
    
    # Mostrar autors disponibles
    print("📚 Autors predefinits:")
    for clau, autor in AUTORS_CLASSICS.items():
        print(f"   - {clau}: {autor['nom']} ({autor['genere']})")
    print()
    
    # Previsualitzar prompt de prova
    print("🎨 Exemple de prompt (Plató):")
    print("-" * 40)
    prompt_info = previsualitzar_prompt(
        nom="Plató",
        epoca="Grècia clàssica, s. V-IV aC",
        genere="FIL",
    )
    print(f"PROMPT:\n{prompt_info['prompt']}\n")
    print(f"NEGATIVE:\n{prompt_info['negative_prompt']}\n")
    
    # Generar si es demana
    if "--generate" in sys.argv and agent.venice:
        autor = sys.argv[sys.argv.index("--generate") + 1] if len(sys.argv) > sys.argv.index("--generate") + 1 else "plato"
        print(f"\n🖼️  Generant retrat de '{autor}'...")
        try:
            path = generar_autor_classic(autor, "output/autors")
            print(f"✅ Retrat guardat: {path}")
        except Exception as e:
            print(f"❌ Error: {e}")
