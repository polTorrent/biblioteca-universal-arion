"""Agent per a la generació de portades de llibres minimalistes i simbòliques.

Utilitza Venice.ai per generar imatges.
Estil visual: MINIMALISTA FIGURATIU - siluetes i objectes simplificats, 60%+ espai buit.
Format: Vertical 2:3 per a llibres.
"""

import io
from pathlib import Path
from typing import Literal

from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, Field

try:
    from agents.base_agent import AgentConfig, AgentResponse, BaseAgent
    from agents.venice_client import VeniceClient, VeniceError
except ImportError:
    from base_agent import AgentConfig, AgentResponse, BaseAgent
    from venice_client import VeniceClient, VeniceError


GenreLiterari = Literal["FIL", "POE", "TEA", "NOV", "SAG", "ORI", "EPO"]


class PaletaGenere(BaseModel):
    """Paleta de colors i estil per a un gènere literari."""
    colors: list[str]
    estil: str
    descripcio: str
    background: str
    accent: str
    text_color: str = "#1A1A1A"


PALETES: dict[str, PaletaGenere] = {
    "FIL": PaletaGenere(
        colors=["warm cream", "charcoal gray", "terracotta", "aged paper"],
        estil="minimalist figurative silhouette",
        descripcio="Simple symbolic object silhouette, classical, elegant",
        background="#F5F1E8",
        accent="#3D3D3D",
        text_color="#1A1A1A",
    ),
    "POE": PaletaGenere(
        colors=["soft blue", "dusty rose", "pearl white", "sage green"],
        estil="delicate figurative watercolor",
        descripcio="Single poetic object, soft edges, dreamlike atmosphere",
        background="#F8F6F4",
        accent="#6B5B73",
        text_color="#3D2E35",
    ),
    "TEA": PaletaGenere(
        colors=["deep black", "rich crimson", "antique gold", "burgundy"],
        estil="dramatic figurative theatrical",
        descripcio="Bold theatrical symbol, dramatic lighting, stage presence",
        background="#1A1A1A",
        accent="#B8860B",
        text_color="#F5F5F5",
    ),
    "NOV": PaletaGenere(
        colors=["sepia", "misty blue", "forest green", "cream"],
        estil="atmospheric figurative narrative",
        descripcio="Evocative object silhouette, storytelling mood, nostalgic",
        background="#F5F0E8",
        accent="#4A5568",
        text_color="#2D3748",
    ),
    "SAG": PaletaGenere(
        colors=["deep blue", "luminous gold", "pure white", "celestial"],
        estil="sacred figurative iconic",
        descripcio="Sacred symbol, luminous presence, transcendent simplicity",
        background="#0D1B2A",
        accent="#D4AF37",
        text_color="#F0E6D3",
    ),
    "ORI": PaletaGenere(
        colors=["sumi ink black", "rice paper white", "vermillion red"],
        estil="zen ink wash sumi-e",
        descripcio="Single brushstroke object, Japanese aesthetic, ma space",
        background="#FAF8F5",
        accent="#8B0000",
        text_color="#2C1810",
    ),
    "EPO": PaletaGenere(
        colors=["warm sepia", "terracotta", "muted teal", "sand"],
        estil="minimalist watercolor illustration",
        descripcio="Simple elegant watercolor silhouette, ancient symbol",
        background="#F5F0E6",
        accent="#8B6914",
        text_color="#3D2B1F",
    ),
}

# Símbols figuratius per temes específics
SIMBOLS_TEMATICS: dict[str, str] = {
    # Filosofia
    "estoïcisme": "a single ancient Greek column fragment",
    "temps": "a minimalist hourglass with falling sand",
    "mort": "a single wilting flower stem",
    "virtut": "a simple laurel branch",
    "ànima": "a delicate feather floating",
    "raó": "a single candle flame illuminating",
    "llibertat": "broken chain links",
    "deure": "an old iron key",
    "presó": "vertical iron bars with light between",
    "diàleg": "two facing silhouette profiles",
    "coneixement": "an open ancient book",
    "veritat": "a simple mirror reflection",
    "saviesa": "an owl silhouette",
    "natura": "a single gnarled tree",
    "voluntat": "a clenched fist silhouette",
    "representació": "a window frame with landscape",
    "causalitat": "falling dominoes in sequence",
    "lògica": "interlocking geometric shapes",
    "metafísica": "a door slightly ajar with light",
    "epistemologia": "an eye looking through keyhole",
    # Obres específiques
    "conversió": "a heart with flames rising",
    "confessions": "a heart with flames rising",
    "pecat": "a ripe pear on a branch",
    "cicuta": "an ancient greek cup or kylix",
    "sòcrates": "an ancient greek cup or kylix",
    "immortalitat": "a butterfly emerging from cocoon",
    "superhome": "an eagle soaring over mountain peak",
    "zaratustra": "an eagle soaring over mountain peak",
    "àguila": "an eagle soaring over mountain peak",
    "tao": "yin yang symbol in brushstroke style",
    "yin": "water flowing around stones",
    "equilibri": "balanced stones stacked",
    "camí": "a winding mountain path",
    "emperador": "a roman laurel wreath crown",
    "roma": "a roman eagle standard aquila",
    # Poesia
    "amor": "two intertwined roses",
    "melangia": "rain drops on window",
    # Teatre
    "tragèdia": "a cracked theatrical mask",
    "comèdia": "a smiling mask with shadow",
    # Novel·la / Terror gòtic
    "viatge": "a sailing ship silhouette",
    "guerra": "a broken sword",
    "família": "an empty chair by window",
    "gòtic": "a gothic castle silhouette against moonlight",
    "terror": "a single human eye in darkness",
    "misteri": "an ornate keyhole with light behind",
    "castell": "a gothic castle tower silhouette",
    "fantasma": "a translucent veil floating",
    "boira": "mist rising from water",
    "nit": "a crescent moon behind clouds",
    "ombra": "a long shadow cast by candlelight",
    # Art i pintura
    "retrat": "an ornate oval picture frame, empty, gilded",
    "oval": "an ornate oval picture frame, empty, gilded",
    "pintura": "a painter's palette with brushes",
    "pintor": "a single paintbrush with wet tip",
    "art": "an artist easel with blank canvas",
    "artista": "a painter's palette with brushes",
    "quadre": "an ornate picture frame casting shadow",
    "tela": "a stretched canvas on wooden frame",
    "cavallet": "an artist easel silhouette",
    # Oriental
    "zen": "a single lotus flower",
    "bushido": "a katana blade reflection",
    "bambú": "bamboo stalks in mist",
    "foc": "dancing flames",
    "infern": "flames rising from below",
    "sacrifici": "hands releasing a bird",
    "obsessió": "an eye in shadow staring",
    # Epopeia
    "heroi": "a shield and spear crossed",
    "déus": "lightning bolt from clouds",
    "batalla": "a single warrior helmet",
    # Obres clàssiques específiques
    "odissea": "an ancient Greek trireme ship with single sail on waves",
    "ulisses": "an ancient Greek trireme ship with single sail on waves",
    "odisseu": "an ancient Greek trireme ship with single sail on waves",
    "ítaca": "an ancient Greek trireme ship with single sail on waves",
    "eneida": "the wooden Trojan horse silhouette",
    "enees": "the wooden Trojan horse silhouette",
    "troia": "the wooden Trojan horse silhouette",
    # Poe i terror americà
    "poe": "a black raven perched on skull",
    "corb": "a black raven silhouette",
    "enterrat": "a coffin lid slightly open",
    "cor": "an anatomical heart silhouette",
    "pèndol": "a swinging pendulum blade",
    "pou": "a dark circular pit from above",
    "usher": "a crumbling mansion facade",
    "gat": "a black cat silhouette with glowing eye",
    # Kafka
    "transformació": "a beetle silhouette from above",
    "metamorfosi": "a beetle silhouette from above",
    "insecte": "a beetle silhouette from above",
    "kafka": "a beetle silhouette from above",
    "procés": "a maze of doors in perspective",
    "burocràcia": "towering filing cabinets",
}


class PromptResult(BaseModel):
    """Resultat de la generació de prompt."""
    prompt: str
    negative_prompt: str
    simbol: str
    raonament: str
    paleta: dict
    genere: str


class PortadistaConfig(BaseModel):
    """Configuració de l'agent portadista."""
    # FORMAT VERTICAL 2:3 per a llibres
    width: int = Field(default=896, ge=512, le=1280)
    height: int = Field(default=1152, ge=512, le=1280)  # Portrait 896x1152 recomanat Venice
    model_imatge: str = "z-image-turbo"
    steps: int = Field(default=30, ge=15, le=50)
    logo_size: int = 65  # Logo més gran


class AgentPortadista(BaseAgent):
    """Agent per generar portades MINIMALISTES FIGURATIVES per a llibres."""

    agent_name = "Portadista"

    LOGO_PATH = Path(__file__).parent.parent / "assets" / "logo" / "arion_logo.png"
    LOGO_PATH_ALT = Path(__file__).parent.parent / "assets" / "logo" / "logo_arion_v1.png"

    # Negative prompt per mantenir minimalisme figuratiu
    NEGATIVE_PROMPT_BASE = (
        "text, letters, words, title, signature, watermark, Venice, logo, "
        "photorealistic, hyper detailed, complex scene, busy composition, cluttered, "
        "multiple main objects, crowded, chaotic, person, human figure, portrait, "
        "full body, hands, decorative border, ornate frame, heavy pattern, "
        "noise, grain, blurry, low quality, amateur"
    )

    def __init__(
        self,
        config: AgentConfig | None = None,
        portadista_config: PortadistaConfig | None = None,
        venice_client: VeniceClient | None = None,
    ) -> None:
        super().__init__(config)
        self.portadista_config = portadista_config or PortadistaConfig()
        try:
            self.venice = venice_client or VeniceClient()
        except VeniceError as e:
            self.log_warning(f"Venice client no disponible: {e}")
            self.venice = None

    @property
    def system_prompt(self) -> str:
        return """Ets un director artístic MINIMALISTA FIGURATIU per a portades de llibres clàssics.

ESTIL:
- Objectes recognoscibles però simplificats (siluetes, formes essencials)
- Un sol element visual central que representi l'essència de l'obra
- 60% espai buit (fons net)
- Colors limitats (2-3 màxim)
- Inspiració: pòsters de pel·lícules minimalistes, il·lustració editorial, art japonès

EXEMPLES DE BONS SÍMBOLS FIGURATIUS:
- Filosofia del temps: rellotge de sorra, espelma consumint-se
- Estoïcisme: columna grega, cadenes trencades
- Presó/deure: clau antiga, barrots amb llum
- Poesia: ploma amb tinta, flor delicada
- Teatre: màscara, focus de llum
- Novel·la: llibre obert, finestra
- Oriental: flor de cirerer, pinzell de tinta
- Epopeia: casc antic, espasa

MAI:
- Text o lletres
- Persones completes o cares
- Escenes complexes
- Múltiples objectes principals"""

    def _obtenir_paleta(self, genere: str) -> PaletaGenere:
        return PALETES.get(genere, PALETES["NOV"])

    def _interpretar_obra_amb_claude(self, metadata: dict) -> str | None:
        """Usa Claude per interpretar l'obra i suggerir un símbol visual apropiat."""
        import subprocess
        import json

        titol = metadata.get("titol", "")
        autor = metadata.get("autor", "")
        descripcio = metadata.get("descripcio", "")

        if not titol:
            return None

        prompt = f"""Ets un director artístic. Per a una portada de llibre MINIMALISTA FIGURATIVA,
suggereix UN SOL objecte visual que representi l'essència d'aquesta obra:

Títol: {titol}
Autor: {autor}
Descripció: {descripcio}

REGLES:
- Un sol objecte físic, tangible, recognoscible
- Res de persones, cares o figures humanes completes
- Ha de ser un objecte que es pugui dibuixar com a silueta elegant
- Màxim 8 paraules en anglès

EXEMPLES BONS:
- Per "El retrat oval" de Poe: "an ornate oval gilded picture frame"
- Per "La metamorfosi" de Kafka: "a beetle silhouette from above"
- Per "El cor delator" de Poe: "an anatomical heart under floorboards"

Respon NOMÉS amb l'objecte en anglès, sense explicacions."""

        try:
            result = subprocess.run(
                ["claude", "-p", prompt, "--output-format", "json"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    simbol = data.get("result", "").strip()
                except json.JSONDecodeError:
                    simbol = result.stdout.strip()

                # Validar que no sigui massa llarg
                if simbol and len(simbol.split()) <= 12:
                    self.log_info(f"Claude suggereix: {simbol}")
                    return simbol
        except Exception as e:
            self.log_warning(f"Error interpretant obra amb Claude: {e}")

        return None

    def _generar_prompt_automatic(self, metadata: dict, paleta: PaletaGenere, genere: str) -> dict:
        """Genera prompt FIGURATIU MINIMALISTA basat en el contingut de l'obra."""
        titol = metadata.get("titol", "").lower()
        temes = metadata.get("temes", [])
        descripcio = metadata.get("descripcio", "").lower()
        autor = metadata.get("autor", "").lower()

        simbol = None
        tema_trobat = None

        # 1. PRIORITAT MÀXIMA: Buscar paraules clau al TÍTOL (més específic)
        for clau, simbol_candidat in SIMBOLS_TEMATICS.items():
            if clau in titol:
                simbol = simbol_candidat
                tema_trobat = f"títol ({clau})"
                break

        # 2. Si no, buscar a la DESCRIPCIÓ (context de l'obra)
        if not simbol:
            for clau, simbol_candidat in SIMBOLS_TEMATICS.items():
                if clau in descripcio:
                    simbol = simbol_candidat
                    tema_trobat = f"descripció ({clau})"
                    break

        # 3. Si no, buscar pels TEMES explícits
        if not simbol:
            for tema in temes:
                tema_lower = tema.lower()
                if tema_lower in SIMBOLS_TEMATICS:
                    simbol = SIMBOLS_TEMATICS[tema_lower]
                    tema_trobat = f"tema ({tema})"
                    break

        # 4. Si no, buscar per l'AUTOR (per estils característics)
        if not simbol:
            for clau, simbol_candidat in SIMBOLS_TEMATICS.items():
                if clau in autor:
                    simbol = simbol_candidat
                    tema_trobat = f"autor ({clau})"
                    break

        # 5. Si encara no hi ha símbol, usar Claude per interpretar l'obra
        if not simbol:
            simbol_claude = self._interpretar_obra_amb_claude(metadata)
            if simbol_claude:
                simbol = simbol_claude
                tema_trobat = "interpretació IA"

        # 6. Símbols per defecte segons gènere (només si res més funciona)
        simbols_defecte = {
            "FIL": "a single ancient oil lamp glowing softly",
            "POE": "a quill pen with ink drop",
            "TEA": "a spotlight beam on empty stage",
            "NOV": "an old leather-bound book slightly open",
            "SAG": "rays of light through stained glass",
            "ORI": "a single cherry blossom branch",
            "EPO": "an ancient bronze helmet in profile",
        }

        if not simbol:
            simbol = simbols_defecte.get(genere, simbols_defecte["NOV"])
            tema_trobat = "gènere per defecte"

        # Construir prompt figuratiu minimalista
        prompt = (
            f"Minimalist book cover illustration, {simbol}, "
            f"centered composition, {paleta.estil} style, "
            f"{' and '.join(paleta.colors[:2])} color palette, "
            f"60 percent negative space, clean solid background, "
            f"single object focus, elegant simplicity, "
            f"fine art quality, editorial design, subtle shadows, "
            f"no text, sophisticated, museum poster aesthetic"
        )

        return {
            "prompt": prompt,
            "negative_prompt": self.NEGATIVE_PROMPT_BASE,
            "simbol": simbol,
            "raonament": f"Símbol figuratiu basat en: {tema_trobat}",
            "paleta": paleta.model_dump(),
            "genere": genere,
        }

    def crear_prompt(self, metadata: dict) -> dict:
        """Genera prompt artístic ULTRA-MINIMALISTA."""
        genere = metadata.get("genere", "NOV")
        paleta = self._obtenir_paleta(genere)

        # Usar sempre el generador automàtic per consistència minimalista
        return self._generar_prompt_automatic(metadata, paleta, genere)

    def _carregar_fonts(self, mida_titol_override: int | None = None) -> tuple:
        """Carrega fonts elegants pel text.

        Args:
            mida_titol_override: Si es proporciona, usa aquesta mida pel títol
                                (per títols llargs que necessiten font més petita)
        """
        height = self.portadista_config.height

        # Mides base (més grans i professionals)
        mida_titol = mida_titol_override or int(height * 0.055)
        mida_autor = int(height * 0.042)  # Encara més gran
        mida_editorial = int(height * 0.018)

        # Fonts per ordre de preferència
        fonts_serif = [
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
        ]
        fonts_serif_regular = [
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
        ]
        fonts_sans = [
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        ]

        def carregar_font(llista_fonts, mida):
            for font_path in llista_fonts:
                try:
                    return ImageFont.truetype(font_path, mida)
                except OSError:
                    continue
            return ImageFont.load_default()

        font_titol = carregar_font(fonts_serif, mida_titol)
        font_autor = carregar_font(fonts_serif_regular, mida_autor)
        font_editorial = carregar_font(fonts_sans, mida_editorial)

        return font_titol, font_autor, font_editorial

    def _eliminar_fons_blanc(self, img: Image.Image, threshold: int = 250) -> Image.Image:
        """Converteix píxels blancs a transparents."""
        data = img.getdata()
        new_data = []
        for item in data:
            if item[0] > threshold and item[1] > threshold and item[2] > threshold:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        img.putdata(new_data)
        return img

    def _crear_logo_cercle(self, logo_path: Path, size: int) -> Image.Image | None:
        """Crea el logo dins un cercle blanc amb vora negra, renderitzat a alta resolució."""
        try:
            logo_original = Image.open(logo_path).convert("RGBA")
            logo_original = self._eliminar_fons_blanc(logo_original)
            
            # Renderitzar a 4x per antialiasing
            scale = 4
            big_size = size * scale
            
            circle_img = Image.new("RGBA", (big_size, big_size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(circle_img)
            
            # Cercle blanc amb vora negra fina
            border = max(4, int(big_size * 0.025))
            draw.ellipse(
                [border, border, big_size - border - 1, big_size - border - 1],
                fill="#FFFFFF",
                outline="#1A1A1A",
                width=border
            )
            
            # Logo al 78% del cercle
            inner = int(big_size * 0.78)
            aspect = logo_original.width / logo_original.height
            if aspect > 1:
                w, h = inner, int(inner / aspect)
            else:
                h, w = inner, int(inner * aspect)
            
            logo_resized = logo_original.resize((w, h), Image.Resampling.LANCZOS)
            x, y = (big_size - w) // 2, (big_size - h) // 2
            circle_img.paste(logo_resized, (x, y), logo_resized)
            
            # Reduir amb antialiasing
            return circle_img.resize((size, size), Image.Resampling.LANCZOS)
            
        except Exception as e:
            self.log_warning(f"Error carregant logo: {e}")
            return None

    def _afegir_text_portada(
        self,
        imatge: Image.Image,
        titol: str,
        autor: str,
        editorial: str,
        paleta: PaletaGenere,
    ) -> Image.Image:
        """Afegeix text i logo a la portada amb layout professional."""
        draw = ImageDraw.Draw(imatge)
        width, height = imatge.size
        text_color = paleta.text_color
        margin = int(width * 0.08)
        max_text_width = width - 2 * margin

        # === CALCULAR MIDA ÒPTIMA DEL TÍTOL ===
        titol_text = titol.upper()
        height_ratio = self.portadista_config.height

        # Començar amb mida gran i reduir si cal
        mida_base = int(height_ratio * 0.055)
        mida_minima = int(height_ratio * 0.032)
        mida_titol_final = mida_base

        # Provar mides fins trobar una que càpiga en màxim 3 línies
        for mida in range(mida_base, mida_minima, -2):
            font_test, _, _ = self._carregar_fonts(mida_titol_override=mida)
            linies_test = self._dividir_titol(titol_text, font_test, max_text_width, draw)
            if len(linies_test) <= 3:
                mida_titol_final = mida
                break

        # Carregar fonts amb la mida òptima
        font_titol, font_autor, font_editorial = self._carregar_fonts(mida_titol_override=mida_titol_final)

        # === TÍTOL (a dalt, centrat, possiblement multilínia) ===
        titol_y = int(height * 0.05)
        linies_titol = self._dividir_titol(titol_text, font_titol, max_text_width, draw)

        line_height = int(mida_titol_final * 1.3)  # Espaiat entre línies
        for i, linia in enumerate(linies_titol):
            bbox = draw.textbbox((0, 0), linia, font=font_titol)
            linia_width = bbox[2] - bbox[0]
            x = (width - linia_width) // 2
            draw.text((x, titol_y + i * line_height), linia, font=font_titol, fill=text_color)

        # === AUTOR (a baix, centrat) ===
        autor_y = int(height * 0.83)  # Més amunt per separar del logo
        autor_bbox = draw.textbbox((0, 0), autor, font=font_autor)
        autor_x = (width - (autor_bbox[2] - autor_bbox[0])) // 2
        draw.text((autor_x, autor_y), autor, font=font_autor, fill=text_color)

        # === LOGO + EDITORIAL (centrat a baix) ===
        editorial_y = int(height * 0.92)
        logo_size = self.portadista_config.logo_size

        # Carregar logo
        logo_path = self.LOGO_PATH if self.LOGO_PATH.exists() else self.LOGO_PATH_ALT
        logo = None
        if logo_path.exists():
            logo = self._crear_logo_cercle(logo_path, logo_size)

        # Calcular posicions
        editorial_bbox = draw.textbbox((0, 0), editorial, font=font_editorial)
        editorial_width = editorial_bbox[2] - editorial_bbox[0]
        editorial_height = editorial_bbox[3] - editorial_bbox[1]

        gap = 10
        if logo:
            total_width = logo_size + gap + editorial_width
            start_x = (width - total_width) // 2
            logo_y = editorial_y - (logo_size - editorial_height) // 2
            imatge.paste(logo, (start_x, logo_y), logo)
            text_x = start_x + logo_size + gap
            draw.text((text_x, editorial_y), editorial, font=font_editorial, fill=text_color)
        else:
            text_x = (width - editorial_width) // 2
            draw.text((text_x, editorial_y), editorial, font=font_editorial, fill=text_color)

        return imatge

    def _dividir_titol(self, titol: str, font: ImageFont, max_width: int, draw: ImageDraw) -> list[str]:
        """Divideix el títol en línies que càpiguen dins l'amplada màxima."""
        paraules = titol.split()
        linies = []
        linia_actual = ""

        for paraula in paraules:
            test_linia = f"{linia_actual} {paraula}".strip()
            bbox = draw.textbbox((0, 0), test_linia, font=font)
            test_width = bbox[2] - bbox[0]

            if test_width <= max_width:
                linia_actual = test_linia
            else:
                if linia_actual:
                    linies.append(linia_actual)
                linia_actual = paraula

        if linia_actual:
            linies.append(linia_actual)

        return linies

    def generar_portada(
        self,
        metadata: dict,
        afegir_text: bool = True,
        editorial: str = "Biblioteca Arion",
    ) -> bytes:
        """Genera una portada MINIMALISTA FIGURATIVA completa."""
        if not self.venice:
            raise RuntimeError("Venice client no disponible. Configura VENICE_API_KEY a .env")

        # 1. Generar prompt figuratiu
        self.log_info("Generant prompt figuratiu minimalista...")
        prompt_result = self.crear_prompt(metadata)
        self.log_info(f"Símbol: {prompt_result['simbol']}")
        self.log_info(f"Raonament: {prompt_result['raonament']}")

        # 2. Generar imatge amb Venice (FORMAT VERTICAL)
        self.log_info("Generant imatge amb Venice.ai...")
        image_bytes = self.venice.generar_imatge_sync(
            prompt=prompt_result["prompt"],
            negative_prompt=prompt_result["negative_prompt"],
            width=self.portadista_config.width,
            height=self.portadista_config.height,
            model=self.portadista_config.model_imatge,
            steps=self.portadista_config.steps,
        )

        # 3. Afegir text i logo
        if afegir_text:
            self.log_info("Afegint text i logo...")
            imatge = Image.open(io.BytesIO(image_bytes))
            paleta = self._obtenir_paleta(prompt_result["genere"])
            imatge = self._afegir_text_portada(
                imatge,
                metadata.get("titol", "Sense títol"),
                metadata.get("autor", "Autor desconegut"),
                editorial,
                paleta,
            )
            output = io.BytesIO()
            imatge.save(output, format="PNG", quality=95)
            image_bytes = output.getvalue()

        self.log_info("Portada generada!")
        return image_bytes


def generar_portada_obra(
    titol: str,
    autor: str,
    genere: str = "NOV",
    temes: list[str] | None = None,
    descripcio: str = "",
    output_path: Path | str | None = None,
) -> bytes:
    """Funció ràpida per generar una portada."""
    agent = AgentPortadista()
    metadata = {
        "titol": titol,
        "autor": autor,
        "genere": genere,
        "temes": temes or [],
        "descripcio": descripcio,
    }
    portada_bytes = agent.generar_portada(metadata)
    
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(portada_bytes)
        print(f"✅ Portada: {path}")
    
    return portada_bytes


if __name__ == "__main__":
    import sys

    print("=" * 50)
    print("TEST PORTADISTA FIGURATIU MINIMALISTA")
    print("=" * 50)

    agent = AgentPortadista()
    print(f"✅ Agent creat")
    print(f"   Venice: {'✅' if agent.venice else '❌'}")
    print(f"   Format: {agent.portadista_config.width}x{agent.portadista_config.height}")

    if agent.venice and "--generate" in sys.argv:
        test = {
            "titol": "Meditacions",
            "autor": "Marc Aureli",
            "genere": "FIL",
            "temes": ["estoïcisme", "virtut"],
            "descripcio": "Reflexions filosòfiques sobre la vida i la mort",
        }
        portada = agent.generar_portada(test)
        Path("test_portada.png").write_bytes(portada)
        print("✅ test_portada.png generada")