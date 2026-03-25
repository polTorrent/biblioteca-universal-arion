"""Agent per a la generació de portades de llibres minimalistes i simbòliques.

Utilitza Venice.ai per generar imatges.
Estil visual: MINIMALISTA FIGURATIU - siluetes i objectes simplificats, 60%+ espai buit.
Format: Vertical 2:3 per a llibres.
"""

import hashlib
import io
import os
from pathlib import Path
from typing import Literal

from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, Field

try:
    from agents.base_agent import AgentConfig, BaseAgent
    from agents.venice_client import VeniceClient, VeniceError
except ImportError:
    from base_agent import AgentConfig, BaseAgent
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

# Símbols figuratius per temes específics — cada clau té una llista d'alternatives
# per evitar repeticions entre obres. La selecció es fa per hash de títol+autor.
SIMBOLS_TEMATICS: dict[str, list[str]] = {
    # ── Obres específiques (prioritat alta, al principi per matching primer) ──
    # NOTA: entrades multi-paraula van PRIMER per evitar matchos parcials
    "sutra del cor": [
        "a lotus emerging from perfectly dark water",
        "wooden prayer beads arranged in a circle",
        "an ancient palm leaf manuscript on silk",
    ],
    "cor delator": [
        "an anatomical heart silhouette pulsing under floorboards",
        "a heartbeat line fading to flat silence",
    ],
    "meditacions": [
        "a Roman wax tablet with bronze stylus on field desk",
        "an emperor's signet ring resting on worn marble",
        "a Roman oil lamp glowing on a military campaign table",
        "a philosophical diary open under starlight",
    ],
    "aurora": [
        "a sun rising behind jagged mountain silhouette",
        "dawn light fracturing through storm clouds",
        "a lone mountain peak catching first golden rays",
        "a philosopher's hammer mid-strike on stone tablet",
    ],
    "epístola": [
        "an ancient scroll being carefully unrolled",
        "a wax seal on folded parchment with stylus",
        "a Roman writing reed beside a clay inkwell",
        "a rolled papyrus letter tied with thread",
    ],
    "sonet": [
        "a quill pen resting on parchment with ink drop",
        "an inkwell with a single suspended drop of ink",
        "a lyre wreathed in delicate laurel",
        "a folded sonnet page with wax rose seal",
    ],
    "sonets": [
        "a quill pen casting shadow of a rose",
        "a lute with a single vibrating string",
        "an Elizabethan stage rose with thorns",
        "an ink-stained sonnet scroll tied with silk ribbon",
    ],
    "confessions": [
        "a heart with flames rising",
        "a quill pen dripping ink like tears",
        "an open leather diary lit by candlelight",
    ],
    "conversió": [
        "a heart with flames rising",
        "a chrysalis cracking open to light",
        "a doorway from shadow into radiance",
    ],
    "pecat": [
        "a ripe pear on a branch",
        "a serpent coiled around a fig branch",
        "a cracked golden apple",
    ],
    "cicuta": ["an ancient greek cup or kylix"],
    "sòcrates": [
        "an ancient greek cup or kylix",
        "a hemlock sprig beside a stone cup",
    ],
    "immortalitat": [
        "a butterfly emerging from cocoon",
        "a phoenix feather still glowing embers",
        "an eternal flame on weathered stone altar",
    ],
    "superhome": [
        "an eagle soaring over mountain peak",
        "a lion silhouette roaring at cliff edge",
        "a tightrope walker silhouette over an abyss",
    ],
    "zaratustra": [
        "a hermit descending from a mountain cave at dawn",
        "an eagle soaring over a solitary peak",
        "a rising sun illuminating a serpent and eagle",
    ],
    "àguila": ["an eagle soaring over mountain peak"],
    "tao": [
        "water flowing gently around immovable stones",
        "an empty clay vessel on a rustic wooden table",
        "a mountain waterfall dissolving into soft mist",
        "a single ink brushstroke forming the character for way",
    ],
    "yin": [
        "water flowing around polished river stones",
        "moonlight reflected on a perfectly still lake",
    ],
    "equilibri": [
        "balanced stones stacked on a river shore",
        "two koi fish circling each other in a pool",
        "a tightrope walker's long balance pole",
    ],
    "camí": [
        "a winding mountain path disappearing into mist",
        "stepping stones crossing a quiet stream",
        "a trail vanishing into a bamboo forest",
    ],
    "emperador": [
        "a roman laurel wreath crown on marble",
        "an imperial signet ring with eagle seal",
        "a purple cloak draped over empty marble throne",
    ],
    "roma": [
        "a roman eagle standard aquila",
        "a roman triumphal arch silhouette",
        "the Colosseum in elegant minimalist outline",
    ],
    # Poe i terror americà
    "poe": [
        "a black raven perched on pale skull",
        "a pendulum blade swinging over darkness",
        "a masquerade mask beside a stopped clock",
    ],
    "corb": ["a black raven silhouette on a branch"],
    "enterrat": [
        "a coffin lid slightly open with fingernails marks",
        "a hand pushing through freshly turned earth",
    ],
    "cor": [
        "an anatomical heart silhouette pulsing",
        "a heartbeat line fading to flat silence",
    ],
    "pèndol": ["a sharp pendulum blade swinging in arc"],
    "pou": ["a dark circular pit viewed from above"],
    "usher": ["a crumbling mansion facade reflected in tarn"],
    "gat": ["a black cat silhouette with single glowing eye"],
    # Kafka
    "metamorfosi": ["a beetle silhouette viewed from above"],
    "transformació": [
        "a beetle silhouette from above",
        "a human shadow distorting into strange shape",
    ],
    "insecte": ["a beetle silhouette from above"],
    "kafka": [
        "a beetle silhouette from above",
        "a maze of identical doors in infinite perspective",
        "a bowler hat casting an insect-shaped shadow",
    ],
    "procés": [
        "a maze of identical doors in perspective",
        "towering filing cabinets vanishing upward",
    ],
    "burocràcia": [
        "towering filing cabinets in shadow",
        "an endless corridor of identical numbered doors",
    ],
    # Obres clàssiques
    "odissea": ["an ancient Greek trireme ship with single sail on waves"],
    "ulisses": ["an ancient Greek trireme ship with single sail on waves"],
    "odisseu": ["an ancient Greek trireme ship with single sail on waves"],
    "ítaca": ["an ancient Greek trireme ship with single sail on waves"],
    "eneida": ["the wooden Trojan horse silhouette"],
    "enees": ["the wooden Trojan horse silhouette"],
    "troia": ["the wooden Trojan horse silhouette"],
    "shakespeare": [
        "a quill pen with ink flowing into rose petals",
        "a stage rose intertwined with thorns",
        "the Globe Theatre in delicate silhouette",
        "a sonnet scroll unfurling with scattered petals",
    ],
    "nietzsche": [
        "a philosopher's hammer striking cracked stone",
        "a tightrope walker silhouette over void",
        "a dancing star emerging from cosmic chaos",
        "a mountain peak with a single figure at dawn",
    ],
    # Sèneca
    "lucili": [
        "two hands exchanging an ancient scroll",
        "a sealed letter resting on a Roman desk",
    ],
    "parsimònia": [
        "a single coin on vast empty marble table",
        "a single water drop about to fall from leaf",
    ],
    # ── Filosofia (temes generals) ──
    "estoïcisme": [
        "a single ancient Greek column fragment",
        "a weathered marble hand resting on a sphere",
        "an ancient bronze ring on cracked stone",
        "a stoic's cloak draped over empty bench",
    ],
    "temps": [
        "an ancient water clock with single drop falling",
        "an unwinding spool of golden thread",
        "a sundial casting its longest shadow",
        "sand slipping through weathered fingers",
    ],
    "mort": [
        "a candle flame at the instant of extinguishing",
        "an autumn leaf suspended mid-fall",
        "a moth approaching a dying lantern",
        "a pocket watch stopped at midnight",
    ],
    "virtut": [
        "a simple laurel branch",
        "a polished bronze shield reflecting soft light",
        "a straight arrow pointing skyward",
        "balanced scales on a marble pedestal",
    ],
    "ànima": [
        "a delicate feather floating in still air",
        "a translucent butterfly in warm amber light",
        "a small flame inside a glass sphere",
        "a bird silhouette escaping through open window",
    ],
    "raó": [
        "a crystal prism splitting a beam of light",
        "a compass needle pointing true north",
        "a single candle illuminating an open book",
        "a magnifying glass focusing sunlight",
    ],
    "llibertat": [
        "broken chain links on stone floor",
        "an open birdcage with door swung wide",
        "a kite soaring without its string",
        "a key turning in an open lock",
    ],
    "deure": [
        "an old iron key on velvet",
        "a sealed wax letter on marble",
        "a soldier's helmet resting on his shield",
        "a judge's gavel on aged wood",
    ],
    "presó": [
        "vertical iron bars with light streaming between",
        "a barred window framing distant horizon",
        "a heavy iron door slightly ajar",
        "chains dissolving into wisps of smoke",
    ],
    "diàleg": [
        "two facing silhouette profiles in conversation",
        "two wooden chairs facing each other",
        "a stone bridge connecting two cliff edges",
        "two ancient scrolls unfurled side by side",
    ],
    "coneixement": [
        "an astrolabe silhouette against dark sky",
        "a burning torch in perfect darkness",
        "a seed splitting open with first sprout",
        "an ancient map with compass rose",
    ],
    "veritat": [
        "a veil being gently lifted",
        "a lantern cutting through dense fog",
        "a diamond facet catching pure light",
        "a still pool reflecting a single star",
    ],
    "saviesa": [
        "an ancient gnarled olive tree",
        "an elder's walking staff leaning on wall",
        "a deep well with still water far below",
        "an owl silhouette on bare branch at dusk",
    ],
    "natura": [
        "a river stone worn perfectly smooth by water",
        "a mountain peak barely visible above clouds",
        "a wave frozen at the moment of breaking",
        "a single gnarled tree on a windswept hill",
    ],
    "voluntat": [
        "a hammer striking a glowing anvil",
        "a flame burning steady against strong wind",
        "an arrow at full draw in a longbow",
        "a clenched fist silhouette raised",
    ],
    "representació": [
        "a window frame with distant landscape",
        "a theater curtain half drawn aside",
        "a shadow puppet on an illuminated screen",
        "a painted canvas showing another canvas",
    ],
    "causalitat": [
        "ripples expanding in perfectly still water",
        "a gear mechanism frozen in motion",
        "a pendulum captured mid-swing",
        "falling dominoes in precise sequence",
    ],
    "lògica": [
        "a labyrinth viewed from directly above",
        "a chess knight piece on empty board",
        "nested circles in precise geometric arrangement",
        "interlocking gears in harmony",
    ],
    "metafísica": [
        "a staircase ascending into soft clouds",
        "a mirror reflecting another mirror infinitely",
        "a sphere floating above a dark surface",
        "a door slightly ajar with golden light beyond",
    ],
    "epistemologia": [
        "a telescope pointed at distant stars",
        "a hand reaching toward a point of light",
        "a map with vast uncharted territories",
        "an eye looking through an ornate keyhole",
    ],
    "moral": [
        "a cracked stone tablet of ancient laws",
        "a pair of scales gently tilting",
        "a mask split between light and shadow",
    ],
    "aforisme": [
        "a chisel carving precise letters into marble",
        "a lightning bolt illuminating stone text",
    ],
    "prejudici": [
        "a cracked empty pedestal with nothing on it",
        "shattered stone tablets on the ground",
        "a toppled statue in elegant fragments",
    ],
    # ── Poesia ──
    "amor": [
        "a sealed love letter with crimson wax seal",
        "two hands almost touching across a gap",
        "a lute with one string still vibrating",
        "a rose pressed between pages of a book",
    ],
    "bellesa": [
        "a perfect pearl resting in an open shell",
        "morning dew caught on a spider web",
        "a swan gliding on still water",
        "a prism casting a rainbow on white wall",
    ],
    "mortalitat": [
        "a clock face with no hands",
        "autumn leaves scattered on ancient stone",
        "a sundial in long evening shadow",
        "a single candle burning low in its holder",
    ],
    "melangia": [
        "rain drops trailing down a window pane",
        "a willow tree bending in autumn wind",
        "an empty garden swing in gentle breeze",
    ],
    # ── Teatre ──
    "tragèdia": [
        "a cracked theatrical mask",
        "a broken crown lying on stone steps",
        "a dagger with a single crimson drop",
    ],
    "comèdia": [
        "a smiling mask casting a sad shadow",
        "a jester's bell on a crooked stick",
    ],
    # ── Novel·la ──
    "viatge": [
        "a sailing ship silhouette on horizon",
        "a compass rose with worn brass needle",
        "footprints disappearing into far distance",
    ],
    "guerra": [
        "a broken sword on bare earth",
        "a dented helmet with torn plume",
        "a torn battle flag on a silent field",
    ],
    "família": [
        "an empty chair beside a window",
        "a family portrait frame turned face down",
        "a child's wooden toy left on worn steps",
    ],
    # ── Gòtic / Terror ──
    "gòtic": [
        "a gothic castle silhouette against full moonlight",
        "a stone gargoyle silhouette on a ledge",
        "a wrought iron gate with fog creeping beyond",
    ],
    "terror": [
        "a single human eye wide in darkness",
        "a shadow cast with no visible source",
        "a pale hand emerging from total darkness",
    ],
    "misteri": [
        "an ornate keyhole with light streaming behind",
        "a magnifying glass over an ancient cipher",
        "a sealed wooden box with strange carved symbol",
    ],
    "castell": [
        "a gothic castle tower silhouette at dusk",
        "a drawbridge over a fog-shrouded moat",
    ],
    "fantasma": [
        "a translucent veil floating in empty room",
        "a rocking chair moving on its own",
        "a candle flickering without any wind",
    ],
    "boira": [
        "a lighthouse beam cutting through thick fog",
        "dark trees fading into white coastal mist",
        "mist rising slowly from still black water",
    ],
    "nit": [
        "a single bright star in vast darkness",
        "a solitary window glowing in dark building facade",
        "a crescent moon casting silver on still water",
    ],
    "ombra": [
        "a long shadow with no visible source",
        "a silhouette projected on a sunlit stone wall",
        "a candle casting two crossing shadows",
    ],
    # ── Art i pintura ──
    "retrat": [
        "an ornate oval picture frame, empty, gilded",
        "a painter's easel with canvas covered by cloth",
        "a gilded hand mirror lying face down",
    ],
    "oval": ["an ornate oval picture frame, empty, gilded"],
    "pintura": [
        "a painter's palette with fresh oil colors",
        "a single bold brushstroke of deep vermillion",
        "paint dripping from a suspended brush tip",
    ],
    "pintor": [
        "a single paintbrush with wet glistening tip",
        "a palette knife edge with thick fresh paint",
    ],
    "art": [
        "an artist easel with blank white canvas",
        "a sculptor's chisel beside a marble fragment",
    ],
    "artista": ["a painter's palette with well-used brushes"],
    "quadre": [
        "an ornate picture frame casting dramatic shadow",
        "a canvas with one single bold impasto stroke",
    ],
    "tela": ["a stretched canvas on worn wooden frame"],
    "cavallet": ["an artist easel silhouette in studio light"],
    # ── Oriental ──
    "zen": [
        "a stone garden with precisely raked sand patterns",
        "a ceramic tea bowl on woven tatami",
        "an enso circle drawn in single brushstroke",
        "a single smooth river stone on raked gravel",
    ],
    "bushido": [
        "a katana blade reflecting moonlight",
        "a samurai helmet with crescent moon crest",
        "cherry blossoms falling onto a still blade",
    ],
    "bambú": [
        "bamboo stalks disappearing into mountain mist",
        "a single bamboo shoot breaking through cracked stone",
    ],
    "buda": [
        "a bodhi tree with vast spreading roots",
        "a lotus emerging from dark muddy water",
        "an empty meditation cushion in bare room",
    ],
    "sutra": [
        "a lotus emerging from perfectly dark water",
        "wooden prayer beads arranged in a circle",
        "an ancient palm leaf manuscript on silk",
    ],
    "foc": [
        "a single match at the instant of igniting",
        "embers glowing deep orange in darkness",
        "dancing flames reflected in still water",
    ],
    "infern": [
        "flames rising from cracked earth below",
        "a cracked earth surface revealing fire beneath",
    ],
    "sacrifici": [
        "hands releasing a white bird skyward",
        "a broken sword laid upon a stone altar",
    ],
    "obsessió": [
        "a moth spiraling helplessly toward a flame",
        "a clock with hands spinning wildly",
        "an eye in deep shadow staring unblinking",
    ],
    # ── Epopeia ──
    "heroi": [
        "a lone warrior's shadow stretching at dusk",
        "a hero's worn sandal on ancient stone step",
        "a shield and bronze spear crossed",
    ],
    "déus": [
        "lightning bolt descending from dark clouds",
        "Mount Olympus peak glimpsed through clouds",
        "a divine hand reaching through parting clouds",
    ],
    "batalla": [
        "a single ancient warrior helmet in profile",
        "arrows lodged deep in a wooden shield",
        "a bronze war horn silhouette",
    ],
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

EXEMPLES DE BONS SÍMBOLS FIGURATIUS (varietat és clau, MAI repetir entre obres):
- Filosofia estoica: tauleta de cera romana, anell de bronze, capa sobre banc buit
- Temps i mortalitat: rellotge d'aigua, fil d'or desfent-se, rellotge de butxaca aturat
- Llibertat: gàbia oberta, estel sense fil, cadenes dissolent-se en fum
- Poesia: lira amb llorer, ploma projectant ombra de rosa, tinter amb gota suspesa
- Teatre: corona trencada en graons, daga amb una sola gota
- Novel·la/gòtic: porta de ferro entreoberta, gàrgola en silenci, fanals en boira
- Oriental: jardí zen amb sorra rastrejada, bol de te sobre tatami, enso en pinzellada
- Epopeia: sandàlia d'heroi en pedra antiga, corn de guerra, casc de guerrer
- Terror: mà emergint de la foscor, finestra solitària il·luminada, ombra sense origen
- Art: pinzellada única de vermell intens, cisell al costat de fragment de marbre

MAI:
- Text o lletres
- Persones completes o cares
- Escenes complexes
- Múltiples objectes principals"""

    def _obtenir_paleta(self, genere: str) -> PaletaGenere:
        return PALETES.get(genere, PALETES["NOV"])

    def _seleccionar_simbol(self, opcions: list[str], metadata: dict) -> str:
        """Selecciona un símbol de la llista d'opcions basat en un hash de l'obra.

        Usa un hash determinista de títol+autor per garantir que la mateixa obra
        sempre rep el mateix símbol, però obres diferents amb el mateix tema
        reben símbols diferents.
        """
        if len(opcions) == 1:
            return opcions[0]
        clau = f"{metadata.get('titol', '')}-{metadata.get('autor', '')}".lower()
        h = int(hashlib.md5(clau.encode()).hexdigest(), 16)
        return opcions[h % len(opcions)]

    def _interpretar_obra_amb_claude(self, metadata: dict) -> str | None:
        """Usa Claude per interpretar l'obra i suggerir un símbol visual apropiat."""
        import json
        import subprocess

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
            env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
            result = subprocess.run(
                ["claude", "-p", prompt, "--output-format", "json"],
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
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
        for clau, opcions in SIMBOLS_TEMATICS.items():
            if clau in titol:
                simbol = self._seleccionar_simbol(opcions, metadata)
                tema_trobat = f"títol ({clau})"
                break

        # 2. Si no, buscar a la DESCRIPCIÓ (context de l'obra)
        if not simbol:
            for clau, opcions in SIMBOLS_TEMATICS.items():
                if clau in descripcio:
                    simbol = self._seleccionar_simbol(opcions, metadata)
                    tema_trobat = f"descripció ({clau})"
                    break

        # 3. Si no, buscar pels TEMES explícits
        if not simbol:
            for tema in temes:
                tema_lower = tema.lower()
                if tema_lower in SIMBOLS_TEMATICS:
                    opcions = SIMBOLS_TEMATICS[tema_lower]
                    simbol = self._seleccionar_simbol(opcions, metadata)
                    tema_trobat = f"tema ({tema})"
                    break

        # 4. Si no, buscar per l'AUTOR (per estils característics)
        if not simbol:
            for clau, opcions in SIMBOLS_TEMATICS.items():
                if clau in autor:
                    simbol = self._seleccionar_simbol(opcions, metadata)
                    tema_trobat = f"autor ({clau})"
                    break

        # 5. Si encara no hi ha símbol, usar Claude per interpretar l'obra
        if not simbol:
            simbol_claude = self._interpretar_obra_amb_claude(metadata)
            if simbol_claude:
                simbol = simbol_claude
                tema_trobat = "interpretació IA"

        # 6. Símbols per defecte segons gènere (només si res més funciona)
        simbols_defecte: dict[str, list[str]] = {
            "FIL": [
                "a single ancient oil lamp glowing softly",
                "a philosopher's stone on aged parchment",
                "an abacus with wooden beads",
            ],
            "POE": [
                "a quill pen with ink drop suspended",
                "a dried pressed flower between pages",
                "a nautilus shell cross section",
            ],
            "TEA": [
                "a spotlight beam on empty dark stage",
                "a curtain rope with golden tassel",
                "theatrical footlights in a row",
            ],
            "NOV": [
                "an old leather-bound book slightly open",
                "a pair of reading glasses on worn wood",
                "a bookmark ribbon trailing from closed book",
            ],
            "SAG": [
                "rays of light through stained glass",
                "a sacred chalice with soft glow",
                "a stone cathedral rose window silhouette",
            ],
            "ORI": [
                "a stone lantern in misty garden",
                "a pine branch heavy with fresh snow",
                "a crane in flight over still water",
            ],
            "EPO": [
                "an ancient bronze helmet in profile",
                "a stone tablet with weathered inscription",
                "a war chariot wheel fragment",
            ],
        }

        if not simbol:
            opcions_defecte = simbols_defecte.get(genere, simbols_defecte["NOV"])
            simbol = self._seleccionar_simbol(opcions_defecte, metadata)
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
        img = img.convert("RGBA")
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
        font_titol, font_autor, font_editorial = self._carregar_fonts(
            mida_titol_override=mida_titol_final,
        )

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

    def _dividir_titol(
        self, titol: str, font: ImageFont.FreeTypeFont,
        max_width: int, draw: ImageDraw.ImageDraw,
    ) -> list[str]:
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
            imatge.save(output, format="PNG", compress_level=1)
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
    print("✅ Agent creat")
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
