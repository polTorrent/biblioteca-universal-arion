"""Integració del generador de portades amb el pipeline de traducció.

Aquest mòdul permet generar automàticament portades quan es completa
una traducció, basant-se en les metadades de l'obra.
"""

import logging
from pathlib import Path
from typing import Optional

from agents.portadista import (
    AgentPortadista,
    PortadistaConfig,
    PALETES,
    generar_portada_obra,
)

logger = logging.getLogger(__name__)


class PortadaIntegration:
    """Gestiona la integració de portades amb el pipeline."""

    def __init__(
        self,
        output_dir: Path | str = "output/portades",
        config: PortadistaConfig | None = None,
    ):
        """Inicialitza la integració."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.agent = AgentPortadista(portadista_config=config)

    def generar_per_traduccio(
        self,
        titol: str,
        autor: str,
        genere: str = "NOV",
        temes: list[str] | None = None,
        descripcio: str = "",
        idioma_original: str = "",
    ) -> Optional[Path]:
        """Genera una portada per una traducció completada."""
        if not self.agent.venice:
            logger.warning("Venice client no disponible, saltant generació de portada")
            return None

        # Nom de fitxer segur
        nom_base = titol.lower()
        for char in " '-àèéíòóúïü":
            nom_base = nom_base.replace(char, "_")
        nom_fitxer = f"{nom_base}_portada.png"
        output_path = self.output_dir / nom_fitxer

        try:
            metadata = {
                "titol": titol,
                "autor": autor,
                "genere": genere,
                "temes": temes or [],
                "descripcio": descripcio or f"Traducció de l'original en {idioma_original}",
            }

            logger.info(f"Generant portada per: {titol}")
            portada = self.agent.generar_portada(metadata)
            output_path.write_bytes(portada)
            logger.info(f"Portada guardada: {output_path}")

            return output_path

        except Exception as e:
            logger.error(f"Error generant portada: {e}")
            return None


def afegir_portada_a_resultat(
    pipeline_result: dict,
    metadata: dict,
    output_dir: Path | str = "output/portades",
) -> dict:
    """Afegeix una portada a un resultat del pipeline."""
    integration = PortadaIntegration(output_dir=output_dir)

    portada_path = integration.generar_per_traduccio(
        titol=metadata.get("titol", "Obra Traduïda"),
        autor=metadata.get("autor", "Autor Desconegut"),
        genere=metadata.get("genere", "NOV"),
        temes=metadata.get("temes"),
        descripcio=metadata.get("descripcio", ""),
        idioma_original=pipeline_result.get("source_language", ""),
    )

    if portada_path:
        pipeline_result["portada_path"] = str(portada_path)

    return pipeline_result


def detectar_genere(text: str, idioma: str = "") -> str:
    """Intenta detectar el gènere literari d'un text."""
    text_lower = text.lower()

    indicadors = {
        "TEA": ["personatges:", "escena:", "acte", "còr:", "entra", "surt"],
        "POE": ["estrofa", "vers", "rima", "cant"],
        "FIL": ["sòcrates", "plató", "diàleg", "argument", "proposició"],
        "SAG": ["déu", "senyor", "profeta", "esperit", "ànima"],
        "EPO": ["heroi", "batalla", "déus", "cant", "ira"],
        "ORI": ["tao", "buda", "dharma", "zen", "confuci"],
    }

    if idioma in ["xinès", "japonès", "sànscrit", "pali"]:
        return "ORI"

    scores = {genere: 0 for genere in indicadors}
    for genere, paraules in indicadors.items():
        for paraula in paraules:
            if paraula in text_lower:
                scores[genere] += 1

    max_score = max(scores.values())
    if max_score > 0:
        for genere, score in scores.items():
            if score == max_score:
                return genere

    return "NOV"
