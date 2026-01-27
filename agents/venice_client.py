"""Client per a l'API de Venice.ai - Generació d'imatges per portades."""

import asyncio
import os
from typing import Literal

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


class VeniceError(Exception):
    """Error genèric del client Venice."""
    pass


class VeniceAPIKeyError(VeniceError):
    """Error quan no es troba la clau API."""
    pass


class VeniceRequestError(VeniceError):
    """Error en una petició a l'API."""
    pass


class ImageGenerationRequest(BaseModel):
    """Petició de generació d'imatge."""

    prompt: str
    negative_prompt: str = ""
    width: int = Field(default=1024, ge=512, le=1280)   # Venice API limit: 1280
    height: int = Field(default=1280, ge=512, le=1280)  # Venice API limit: 1280
    model: str = "z-image-turbo"
    steps: int = Field(default=30, ge=10, le=50)
    cfg_scale: float = Field(default=7.5, ge=1.0, le=20.0)
    seed: int | None = None


class ImageModel(BaseModel):
    """Model d'imatge disponible."""

    id: str
    name: str
    type: str


class VeniceClient:
    """Client per a l'API de Venice.ai.

    Genera imatges per a portades de llibres amb format vertical 2:3.

    Exemple d'ús:
        ```python
        client = VeniceClient()

        # Async
        image_bytes = await client.generar_imatge(
            prompt="Ancient Mesopotamian king, epic style",
            negative_prompt="modern, cartoon",
        )

        # Sync
        image_bytes = client.generar_imatge_sync(
            prompt="Ancient Mesopotamian king, epic style",
        )
        ```
    """

    BASE_URL = "https://api.venice.ai/api/v1"

    # Models recomanats per imatges (actualitzat gener 2026)
    MODELS_IMATGE = [
        "z-image-turbo",    # Ràpid i alta qualitat, recomanat
        "nano-banana-pro",  # Suporta resolucions 2K/4K
    ]

    def __init__(self, api_key: str | None = None) -> None:
        """Inicialitza el client Venice.

        Args:
            api_key: Clau API de Venice.ai. Si no es proporciona,
                     es llegeix de la variable d'entorn VENICE_API_KEY.

        Raises:
            VeniceAPIKeyError: Si no es troba cap clau API.
        """
        self.api_key = api_key or os.getenv("VENICE_API_KEY")

        if not self.api_key:
            raise VeniceAPIKeyError(
                "No s'ha trobat VENICE_API_KEY. "
                "Afegeix-la a .env o passa-la com a paràmetre."
            )

        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def generar_imatge(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1536,
        model: str = "z-image-turbo",
        steps: int = 30,
        cfg_scale: float = 7.5,
        seed: int | None = None,
    ) -> bytes:
        """Genera una imatge a partir d'un prompt.

        Args:
            prompt: Descripció de la imatge a generar.
            negative_prompt: Elements a evitar en la imatge.
            width: Amplada en píxels (per defecte 1024 per format 2:3).
            height: Alçada en píxels (per defecte 1536 per format 2:3).
            model: Model a utilitzar (fluently-xl, flux-dev, etc.).
            steps: Nombre de passos de generació (més = més qualitat).
            cfg_scale: Escala de guia del classificador (7-8 recomanat).
            seed: Llavor per reproducibilitat (opcional).

        Returns:
            bytes: Imatge PNG en bytes.

        Raises:
            VeniceRequestError: Si la petició falla.
        """
        request = ImageGenerationRequest(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            model=model,
            steps=steps,
            cfg_scale=cfg_scale,
            seed=seed,
        )

        payload = {
            "model": request.model,
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt,
            "aspect_ratio": "2:3",  # Format vertical per portades
            "width": request.width,
            "height": request.height,
            "steps": request.steps,
            "cfg_scale": request.cfg_scale,
            "hide_watermark": True,   # Amaga watermark
            "safe_mode": False,       # No difumina contingut
            "format": "png",          # Millor qualitat
        }

        if request.seed is not None:
            payload["seed"] = request.seed

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    f"{self.BASE_URL}/image/generate",
                    headers=self._headers,
                    json=payload,
                )

                if response.status_code == 401:
                    raise VeniceAPIKeyError("Clau API invàlida o expirada.")

                if response.status_code == 429:
                    raise VeniceRequestError("Límit de peticions excedit. Espera uns minuts.")

                if response.status_code != 200:
                    error_detail = response.text[:500] if response.text else "Sense detalls"
                    raise VeniceRequestError(
                        f"Error {response.status_code} de l'API Venice: {error_detail}"
                    )

                # L'API pot retornar JSON amb URL o directament bytes
                content_type = response.headers.get("content-type", "")

                if "application/json" in content_type:
                    data = response.json()
                    # Si retorna URL, descarregar la imatge
                    if "url" in data:
                        image_response = await client.get(data["url"])
                        return image_response.content
                    elif "image" in data:
                        # Base64 encoded
                        import base64
                        return base64.b64decode(data["image"])
                    elif "images" in data and len(data["images"]) > 0:
                        # Array d'imatges en base64
                        import base64
                        return base64.b64decode(data["images"][0])
                    else:
                        raise VeniceRequestError(f"Format de resposta desconegut: {data.keys()}")

                # Resposta directa en bytes (PNG)
                return response.content

            except httpx.TimeoutException:
                raise VeniceRequestError("Temps d'espera excedit. La generació pot trigar.")
            except httpx.RequestError as e:
                raise VeniceRequestError(f"Error de connexió: {e}")

    async def llistar_models(
        self,
        tipus: Literal["image", "text", "all"] = "image",
    ) -> list[ImageModel]:
        """Llista els models disponibles.

        Args:
            tipus: Filtrar per tipus ("image", "text", "all").

        Returns:
            list[ImageModel]: Llista de models disponibles.

        Raises:
            VeniceRequestError: Si la petició falla.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/models",
                    headers=self._headers,
                )

                if response.status_code != 200:
                    raise VeniceRequestError(
                        f"Error {response.status_code} obtenint models"
                    )

                data = response.json()
                models = []

                # Estructura de resposta pot variar
                model_list = data.get("data", data.get("models", []))

                for model_data in model_list:
                    model_type = model_data.get("type", "unknown")

                    if tipus == "all" or model_type == tipus:
                        models.append(ImageModel(
                            id=model_data.get("id", ""),
                            name=model_data.get("name", model_data.get("id", "")),
                            type=model_type,
                        ))

                return models

            except httpx.RequestError as e:
                raise VeniceRequestError(f"Error de connexió: {e}")

    def generar_imatge_sync(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1536,
        model: str = "z-image-turbo",
        steps: int = 30,
        cfg_scale: float = 7.5,
        seed: int | None = None,
    ) -> bytes:
        """Versió síncrona de generar_imatge.

        Útil per a scripts que no utilitzen asyncio.

        Args:
            Mateixos paràmetres que generar_imatge().

        Returns:
            bytes: Imatge PNG en bytes.
        """
        return asyncio.run(
            self.generar_imatge(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                model=model,
                steps=steps,
                cfg_scale=cfg_scale,
                seed=seed,
            )
        )

    def llistar_models_sync(
        self,
        tipus: Literal["image", "text", "all"] = "image",
    ) -> list[ImageModel]:
        """Versió síncrona de llistar_models."""
        return asyncio.run(self.llistar_models(tipus))


def generar_portada_llibre(
    titol: str,
    autor: str,
    estil: str = "classical oil painting",
    epoca: str = "",
    elements: list[str] | None = None,
) -> bytes:
    """Funció d'ajuda per generar portades de llibres.

    Args:
        titol: Títol del llibre (per inspirar la imatge).
        autor: Autor del llibre.
        estil: Estil artístic ("classical oil painting", "watercolor", etc.).
        epoca: Època històrica ("ancient mesopotamia", "classical greece", etc.).
        elements: Elements visuals a incloure.

    Returns:
        bytes: Imatge PNG de la portada.

    Exemple:
        ```python
        portada = generar_portada_llibre(
            titol="L'Epopeia de Gilgamesh",
            autor="Anònim mesopotàmic",
            estil="ancient relief carving style",
            epoca="ancient mesopotamia",
            elements=["hero", "lion", "ziggurat", "cuneiform"],
        )
        Path("portada_gilgamesh.png").write_bytes(portada)
        ```
    """
    elements_str = ", ".join(elements) if elements else ""

    prompt_parts = [
        f"Book cover illustration for '{titol}'",
        f"by {autor}" if autor else "",
        f"in {estil} style",
        f"set in {epoca}" if epoca else "",
        elements_str,
        "highly detailed, professional quality, suitable for book cover",
        "vertical composition, dramatic lighting",
    ]

    prompt = ", ".join(part for part in prompt_parts if part)

    negative_prompt = (
        "text, title, letters, watermark, signature, "
        "low quality, blurry, distorted, cartoon, anime, "
        "modern elements, contemporary clothing"
    )

    client = VeniceClient()
    return client.generar_imatge_sync(
        prompt=prompt,
        negative_prompt=negative_prompt,
        width=1024,
        height=1536,  # Format 2:3 vertical per portades
        model="flux-2-max",
        steps=35,
        cfg_scale=8.0,
    )


if __name__ == "__main__":
    # Test del client
    import sys

    print("Test del client Venice.ai")
    print("=" * 50)

    try:
        client = VeniceClient()
        print("✅ Client inicialitzat correctament")

        # Llistar models
        print("\nModels d'imatge disponibles:")
        models = client.llistar_models_sync("image")
        for model in models:
            print(f"  - {model.id}: {model.name}")

        # Generar imatge de prova
        if len(sys.argv) > 1 and sys.argv[1] == "--test-image":
            print("\nGenerant imatge de prova...")
            image_bytes = client.generar_imatge_sync(
                prompt="Ancient Mesopotamian hero, epic style, dramatic lighting",
                negative_prompt="modern, cartoon",
                width=512,
                height=768,
                steps=20,
            )
            from pathlib import Path
            output_path = Path("test_venice.png")
            output_path.write_bytes(image_bytes)
            print(f"✅ Imatge guardada a {output_path}")

    except VeniceAPIKeyError as e:
        print(f"❌ Error de clau API: {e}")
        sys.exit(1)
    except VeniceRequestError as e:
        print(f"❌ Error de petició: {e}")
        sys.exit(1)
