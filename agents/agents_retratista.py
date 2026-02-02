"""Agent per a la generació de retrats d'autors amb estil Rotoscòpia Sepia.

Utilitza imatges reals de Wikimedia Commons i Venice.ai /image/edit per
aplicar un estil artístic elegant i recogneixible.

Estil visual: Rotoscòpia sepia - fotos reals estilitzades amb tons càlids.
Format: Quadrat per avatars (512x512).

Exemple d'ús:
    ```python
    from agents.agents_retratista import AgentRetratista, generar_retrat_autor

    # Ús ràpid
    retrat = generar_retrat_autor(
        nom="Vsévolod Garxin",
        nom_wikimedia="Vsevolod Garshin",
        output_path="autors/garxin.png",
    )

    # Ús amb agent
    agent = AgentRetratista()
    retrat = agent.generar_retrat({
        "nom": "Sèneca",
        "nom_wikimedia": "Seneca",
    })
    ```
"""

import io
import os
import requests
from pathlib import Path
from PIL import Image
from pydantic import BaseModel, Field

from agents.base_agent import AgentConfig, BaseAgent


# ═══════════════════════════════════════════════════════════════════════════
# PROMPT D'ESTIL ROTOSCÒPIA SEPIA
# ═══════════════════════════════════════════════════════════════════════════

PROMPT_ROTOSCOPIA_SEPIA = (
    "Transform into elegant rotoscope illustration style, "
    "sepia warm tones, vintage editorial portrait, "
    "artistic posterized effect, classic book illustration aesthetic, "
    "no text, no letters, no words, no watermarks"
)

# Prompts alternatius per si es volen afegir més estils
PROMPTS_ESTIL = {
    "rotoscopia_sepia": PROMPT_ROTOSCOPIA_SEPIA,
    "gravat_antic": (
        "Transform into antique engraving illustration, "
        "19th century encyclopedia style, fine crosshatching, "
        "black ink on cream paper, classical portrait etching"
    ),
    "sketch_llapis": (
        "Transform into elegant pencil sketch portrait, "
        "realistic graphite drawing, soft shading, "
        "artistic portrait on white paper, fine art quality"
    ),
    "duotone_editorial": (
        "Transform into modern duotone portrait, "
        "two-color editorial style, sepia and dark brown only, "
        "minimalist high contrast, magazine cover aesthetic"
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓ DE L'AGENT
# ═══════════════════════════════════════════════════════════════════════════

class RetratistaConfig(BaseModel):
    """Configuració de l'agent retratista."""

    output_size: int = Field(default=512, ge=256, le=1024)
    estil: str = "rotoscopia_sepia"
    fallback_local: bool = True  # Usar PIL si Venice falla


# ═══════════════════════════════════════════════════════════════════════════
# AGENT RETRATISTA
# ═══════════════════════════════════════════════════════════════════════════

class AgentRetratista(BaseAgent):
    """Agent per generar retrats d'autors amb estil Rotoscòpia Sepia.

    Flux:
    1. Buscar imatge real a Wikimedia Commons
    2. Aplicar estil amb Venice /image/edit
    3. Redimensionar i guardar
    """

    agent_name: str = "Retratista"

    WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"
    VENICE_EDIT_API = "https://api.venice.ai/api/v1/image/edit"

    def __init__(
        self,
        config: AgentConfig | None = None,
        retratista_config: RetratistaConfig | None = None,
    ) -> None:
        super().__init__(config)
        self.retratista_config = retratista_config or RetratistaConfig()

        # API key de Venice
        self.venice_api_key = os.getenv("VENICE_API_KEY")
        if self.venice_api_key:
            self.log_info("Venice API configurada")
        else:
            self.log_warning("VENICE_API_KEY no configurada")

        # Headers per Wikimedia (requereix User-Agent)
        self.wikimedia_headers = {
            "User-Agent": "BibliotecaArion/1.0 (https://github.com/biblioteca-arion; contact@arion.cat)"
        }

    def log_error(self, message: str) -> None:
        """Log d'error."""
        self.logger.log_error(self.agent_name, Exception(message))

    @property
    def system_prompt(self) -> str:
        return "Agent per generar retrats d'autors amb estil rotoscòpia sepia."

    def _buscar_imatge_wikimedia(self, nom_autor: str) -> str | None:
        """Busca una imatge de l'autor a Wikimedia Commons.

        Args:
            nom_autor: Nom de l'autor per cercar (en anglès preferiblement)

        Returns:
            URL de la imatge o None si no es troba
        """
        self.log_info(f"Cercant imatge de '{nom_autor}' a Wikimedia...")

        # Cercar fitxers relacionats
        params = {
            "action": "query",
            "list": "search",
            "srsearch": f"{nom_autor} portrait",
            "srnamespace": "6",  # Namespace de fitxers
            "format": "json",
            "srlimit": "5",
        }

        try:
            resp = requests.get(self.WIKIMEDIA_API, params=params, headers=self.wikimedia_headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("query", {}).get("search", [])
            if not results:
                self.log_warning(f"No s'han trobat imatges per '{nom_autor}'")
                return None

            # Agafar el primer resultat
            file_title = results[0]["title"]
            self.log_info(f"Trobat: {file_title}")

            # Obtenir URL directa de la imatge
            params_url = {
                "action": "query",
                "titles": file_title,
                "prop": "imageinfo",
                "iiprop": "url",
                "format": "json",
            }

            resp_url = requests.get(self.WIKIMEDIA_API, params=params_url, headers=self.wikimedia_headers, timeout=10)
            resp_url.raise_for_status()
            data_url = resp_url.json()

            pages = data_url.get("query", {}).get("pages", {})
            for page in pages.values():
                imageinfo = page.get("imageinfo", [{}])[0]
                url = imageinfo.get("url")
                if url:
                    self.log_info(f"URL imatge: {url[:80]}...")
                    return url

            return None

        except Exception as e:
            self.log_error(f"Error cercant a Wikimedia: {e}")
            return None

    def _aplicar_estil_venice(self, image_url: str, estil: str = "rotoscopia_sepia") -> bytes | None:
        """Aplica estil artístic amb Venice /image/edit.

        Args:
            image_url: URL de la imatge original
            estil: Clau de l'estil a aplicar

        Returns:
            bytes de la imatge editada o None si falla
        """
        if not self.venice_api_key:
            self.log_error("Venice API key no configurada")
            return None

        prompt = PROMPTS_ESTIL.get(estil, PROMPT_ROTOSCOPIA_SEPIA)
        self.log_info(f"Aplicant estil '{estil}' amb Venice...")

        headers = {
            "Authorization": f"Bearer {self.venice_api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "prompt": prompt,
            "image": image_url,
        }

        try:
            resp = requests.post(
                self.VENICE_EDIT_API,
                headers=headers,
                json=payload,
                timeout=120,
            )

            if resp.status_code == 200:
                self.log_info("Estil aplicat correctament!")
                return resp.content
            else:
                self.log_error(f"Error Venice: {resp.status_code} - {resp.text[:200]}")
                return None

        except Exception as e:
            self.log_error(f"Error aplicant estil: {e}")
            return None

    def _fallback_sepia_local(self, image_url: str) -> bytes | None:
        """Aplica efecte sepia localment amb PIL (fallback).

        Args:
            image_url: URL de la imatge original

        Returns:
            bytes de la imatge processada o None si falla
        """
        self.log_info("Usant fallback local (PIL)...")

        try:
            # Descarregar imatge
            resp = requests.get(image_url, timeout=30)
            resp.raise_for_status()

            img = Image.open(io.BytesIO(resp.content))
            img.thumbnail((512, 512), Image.Resampling.LANCZOS)

            # Convertir a escala de grisos
            from PIL import ImageOps, ImageEnhance, ImageFilter

            gray = ImageOps.grayscale(img)

            # Augmentar contrast
            enhancer = ImageEnhance.Contrast(gray)
            high_contrast = enhancer.enhance(1.4)

            # Posteritzar
            posterized = ImageOps.posterize(high_contrast, 4)

            # Aplicar to sepia
            sepia = Image.new('RGB', posterized.size)
            pixels_gray = posterized.load()
            pixels_sepia = sepia.load()

            for y in range(posterized.height):
                for x in range(posterized.width):
                    gray_val = pixels_gray[x, y]
                    r = min(255, int(gray_val * 1.05))
                    g = min(255, int(gray_val * 0.88))
                    b = min(255, int(gray_val * 0.68))
                    pixels_sepia[x, y] = (r, g, b)

            # Suavitzar i enfocar
            final = sepia.filter(ImageFilter.SMOOTH_MORE)
            sharpener = ImageEnhance.Sharpness(final)
            final = sharpener.enhance(1.3)

            # Convertir a bytes
            buffer = io.BytesIO()
            final.save(buffer, format="PNG")
            return buffer.getvalue()

        except Exception as e:
            self.log_error(f"Error en fallback local: {e}")
            return None

    def generar_retrat(
        self,
        metadata: dict,
    ) -> bytes:
        """Genera un retrat d'autor.

        Args:
            metadata: Diccionari amb:
                - nom: Nom de l'autor (obligatori)
                - nom_wikimedia: Nom per cercar a Wikimedia (opcional)
                - imatge_url: URL directa de la imatge (opcional)
                - estil: Estil a aplicar (opcional)

        Returns:
            bytes: Imatge PNG del retrat.

        Raises:
            ValueError: Si no es pot obtenir cap imatge.
        """
        nom = metadata.get("nom", "Autor desconegut")
        nom_wikimedia = metadata.get("nom_wikimedia", nom)
        imatge_url = metadata.get("imatge_url")
        estil = metadata.get("estil", self.retratista_config.estil)

        self.log_info(f"Generant retrat de: {nom}")

        # 1. Obtenir URL de la imatge
        if not imatge_url:
            imatge_url = self._buscar_imatge_wikimedia(nom_wikimedia)

        if not imatge_url:
            raise ValueError(f"No s'ha trobat cap imatge per a '{nom}'")

        # 2. Aplicar estil amb Venice
        image_bytes = self._aplicar_estil_venice(imatge_url, estil)

        # 3. Fallback a PIL si Venice falla
        if not image_bytes and self.retratista_config.fallback_local:
            image_bytes = self._fallback_sepia_local(imatge_url)

        if not image_bytes:
            raise ValueError(f"No s'ha pogut processar la imatge de '{nom}'")

        # 4. Redimensionar al tamany final
        img = Image.open(io.BytesIO(image_bytes))
        img.thumbnail(
            (self.retratista_config.output_size, self.retratista_config.output_size),
            Image.Resampling.LANCZOS
        )

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")

        self.log_info(f"Retrat generat: {img.size}")
        return buffer.getvalue()

    def generar_i_guardar(
        self,
        metadata: dict,
        output_path: Path | str,
    ) -> Path:
        """Genera un retrat i el guarda a disc.

        Args:
            metadata: Metadades de l'autor.
            output_path: Ruta on guardar la imatge.

        Returns:
            Path al fitxer generat.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        image_bytes = self.generar_retrat(metadata)
        output_path.write_bytes(image_bytes)

        self.log_info(f"Retrat guardat: {output_path}")
        return output_path


# ═══════════════════════════════════════════════════════════════════════════
# FUNCIONS D'AJUDA
# ═══════════════════════════════════════════════════════════════════════════

def generar_retrat_autor(
    nom: str,
    nom_wikimedia: str | None = None,
    imatge_url: str | None = None,
    estil: str = "rotoscopia_sepia",
    output_path: Path | str | None = None,
) -> bytes:
    """Funció ràpida per generar un retrat d'autor.

    Args:
        nom: Nom de l'autor.
        nom_wikimedia: Nom per cercar a Wikimedia (si diferent).
        imatge_url: URL directa de la imatge (opcional).
        estil: Estil a aplicar (rotoscopia_sepia, gravat_antic, etc.).
        output_path: Ruta on guardar la imatge (opcional).

    Returns:
        bytes: Imatge PNG del retrat.

    Exemple:
        ```python
        retrat = generar_retrat_autor(
            nom="Vsévolod Garxin",
            nom_wikimedia="Vsevolod Garshin",
            output_path="autors/garxin.png",
        )
        ```
    """
    agent = AgentRetratista()

    metadata = {
        "nom": nom,
        "nom_wikimedia": nom_wikimedia or nom,
        "imatge_url": imatge_url,
        "estil": estil,
    }

    image_bytes = agent.generar_retrat(metadata)

    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(image_bytes)
        print(f"✅ Retrat guardat: {path}")

    return image_bytes


# ═══════════════════════════════════════════════════════════════════════════
# AUTORS AMB IMATGES CONEGUDES
# ═══════════════════════════════════════════════════════════════════════════

AUTORS_IMATGES = {
    "plato": {
        "nom": "Plató",
        "nom_wikimedia": "Plato",
    },
    "aristotil": {
        "nom": "Aristòtil",
        "nom_wikimedia": "Aristotle",
    },
    "seneca": {
        "nom": "Sèneca",
        "nom_wikimedia": "Seneca",
    },
    "epictetus": {
        "nom": "Epictetus",
        "nom_wikimedia": "Epictetus",
    },
    "heraclit": {
        "nom": "Heràclit d'Efes",
        "nom_wikimedia": "Heraclitus",
    },
    "schopenhauer": {
        "nom": "Arthur Schopenhauer",
        "nom_wikimedia": "Arthur Schopenhauer",
    },
    "akutagawa": {
        "nom": "Akutagawa Ryūnosuke",
        "nom_wikimedia": "Ryunosuke Akutagawa",
    },
    "garxin": {
        "nom": "Vsévolod Garxin",
        "nom_wikimedia": "Vsevolod Garshin",
    },
}


def generar_autor_conegut(clau: str, output_dir: str = "docs/assets/autors") -> Path:
    """Genera retrat d'un autor amb imatge coneguda.

    Args:
        clau: Clau de l'autor (plato, seneca, garxin, etc.)
        output_dir: Directori de sortida.

    Returns:
        Path al fitxer generat.
    """
    if clau not in AUTORS_IMATGES:
        claus_disponibles = ", ".join(AUTORS_IMATGES.keys())
        raise ValueError(f"Autor '{clau}' no trobat. Disponibles: {claus_disponibles}")

    autor = AUTORS_IMATGES[clau]
    nom_fitxer = clau.lower().replace(" ", "_") + ".png"
    output_path = Path(output_dir) / nom_fitxer

    agent = AgentRetratista()
    return agent.generar_i_guardar(autor, output_path)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN / TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("AGENT RETRATISTA - Rotoscòpia Sepia")
    print("=" * 60)

    agent = AgentRetratista()
    print(f"✅ Agent creat")
    print(f"   Venice: {'✅ Configurada' if agent.venice_api_key else '❌ No configurada'}")
    print(f"   Estil: {agent.retratista_config.estil}")
    print()

    # Mostrar autors disponibles
    print("📚 Autors amb imatges conegudes:")
    for clau, autor in AUTORS_IMATGES.items():
        print(f"   - {clau}: {autor['nom']}")
    print()

    # Mostrar estils disponibles
    print("🎨 Estils disponibles:")
    for estil in PROMPTS_ESTIL.keys():
        print(f"   - {estil}")
    print()

    # Generar si es demana
    if "--generate" in sys.argv:
        idx = sys.argv.index("--generate")
        autor = sys.argv[idx + 1] if len(sys.argv) > idx + 1 else "garxin"
        print(f"\n🖼️  Generant retrat de '{autor}'...")
        try:
            path = generar_autor_conegut(autor)
            print(f"✅ Retrat guardat: {path}")
        except Exception as e:
            print(f"❌ Error: {e}")
