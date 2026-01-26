"""Integració del pipeline de traducció amb la publicació web.

Aquest mòdul permet publicar automàticament una obra quan es completa
la traducció amb el pipeline.
"""

from pathlib import Path

from agents.web_publisher import WebPublisher, WebPublisherConfig, ObraMetadata


def publicar_obra_traduida(
    obra_path: Path | str,
    generar_portada: bool = False,
) -> dict | None:
    """Publica una obra després de completar la traducció.

    Args:
        obra_path: Ruta a la carpeta de l'obra (obres/autor/obra)
        generar_portada: Si True, genera portada amb Venice.ai

    Returns:
        Dict amb informació de publicació o None si error.
    """
    obra_path = Path(obra_path)

    if not obra_path.exists():
        print(f"Error: No existeix {obra_path}")
        return None

    if not (obra_path / "metadata.yml").exists():
        print(f"Error: No existeix metadata.yml a {obra_path}")
        return None

    config = WebPublisherConfig(generar_portades=generar_portada)
    publisher = WebPublisher(publisher_config=config)

    output = publisher.publicar_obra(obra_path, generar_portada=generar_portada)

    if output:
        return {
            "success": True,
            "html_path": str(output),
            "url": f"https://biblioteca-arion.github.io/biblioteca-universal-arion/{output.name}",
        }
    return None


def actualitzar_cataleg() -> dict:
    """Actualitza l'índex i pàgines auxiliars sense regenerar obres.

    Returns:
        Estadístiques d'actualització.
    """
    publisher = WebPublisher()
    return publisher.publicar_tot(generar_portades=False)


class PipelineWebHook:
    """Hook per publicar automàticament després del pipeline.

    Ús:
        hook = PipelineWebHook()
        # Després de completar el pipeline:
        hook.on_translation_complete(obra_path)
    """

    def __init__(self, generar_portades: bool = False):
        self.generar_portades = generar_portades
        self.config = WebPublisherConfig(generar_portades=generar_portades)
        self._publisher: WebPublisher | None = None

    @property
    def publisher(self) -> WebPublisher:
        if self._publisher is None:
            self._publisher = WebPublisher(publisher_config=self.config)
        return self._publisher

    def on_translation_complete(
        self,
        obra_path: Path | str,
        metadata: dict | None = None,
    ) -> dict | None:
        """Callback quan una traducció es completa.

        Args:
            obra_path: Ruta a l'obra traduïda
            metadata: Metadades opcionals del pipeline

        Returns:
            Informació de publicació.
        """
        obra_path = Path(obra_path)
        print(f"\n📚 Publicant obra: {obra_path}")

        result = self.publisher.publicar_obra(
            obra_path,
            generar_portada=self.generar_portades,
        )

        if result:
            print(f"✅ Publicat: {result}")
            # Actualitzar índex
            print("🔄 Actualitzant catàleg...")
            self.publisher._generar_index(
                [self.publisher._llegir_metadata(obra_path)]
            )
            return {
                "success": True,
                "html": str(result),
            }
        else:
            print(f"❌ Error publicant {obra_path}")
            return None
