"""Gestió de l'estat persistent del pipeline de traducció.

Permet reprendre traduccions interrompudes guardant l'estat a disc.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class InfoObra(BaseModel):
    """Informació bàsica de l'obra."""

    autor: str
    titol: str
    llengua: str


class InfoChunks(BaseModel):
    """Estat dels chunks de traducció."""

    total: int = 0
    completats: list[str] = Field(default_factory=list)
    en_curs: str | None = None
    pendents: list[str] = Field(default_factory=list)


class Metriques(BaseModel):
    """Mètriques de qualitat i rendiment."""

    qualitat_mitjana: float = 0.0
    temps_total_min: float = 0.0


class EstatPipelineData(BaseModel):
    """Estructura de dades de l'estat del pipeline."""

    sessio_id: str
    obra: InfoObra
    timestamps: dict[str, str] = Field(default_factory=dict)
    fase_actual: str = "pendent"
    fases_completades: list[str] = Field(default_factory=list)
    chunks: InfoChunks = Field(default_factory=InfoChunks)
    metriques: Metriques = Field(default_factory=Metriques)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class EstatPipeline:
    """Gestor d'estat persistent del pipeline de traducció.

    Guarda l'estat a un fitxer JSON dins el directori de l'obra,
    permetent reprendre traduccions interrompudes.

    Exemple d'ús:
        estat = EstatPipeline(
            obra_dir=Path("obres/filosofia/seneca/brevitate"),
            autor="Sèneca",
            titol="De Brevitate Vitae",
            llengua="llatí"
        )

        if estat.existeix():
            estat.carregar()
            chunks_pendents = estat.obtenir_chunks_pendents()
        else:
            estat.iniciar_fase("glossari")
    """

    def __init__(
        self,
        obra_dir: Path,
        autor: str,
        titol: str,
        llengua: str,
    ) -> None:
        """Inicialitza el gestor d'estat.

        Args:
            obra_dir: Directori de l'obra (ex: obres/filosofia/seneca/brevitate).
            autor: Nom de l'autor.
            titol: Títol de l'obra.
            llengua: Llengua original del text.
        """
        self.obra_dir = Path(obra_dir)
        self.fitxer_estat = self.obra_dir / ".pipeline_state.json"

        # Generar sessio_id
        data_avui = datetime.now().strftime("%Y-%m-%d")
        autor_slug = autor.lower().replace(" ", "-").replace("'", "")[:20]
        titol_slug = titol.lower().replace(" ", "-").replace("'", "")[:20]
        self.sessio_id = f"{autor_slug}-{titol_slug}-{data_avui}"

        # Inicialitzar dades
        ara = datetime.now().isoformat()
        self._data = EstatPipelineData(
            sessio_id=self.sessio_id,
            obra=InfoObra(autor=autor, titol=titol, llengua=llengua),
            timestamps={"inici": ara, "ultima_activitat": ara},
        )

        print(f"[EstatPipeline] Inicialitzat: {self.sessio_id}")

    def existeix(self) -> bool:
        """Comprova si hi ha un estat guardat prèviament.

        Returns:
            True si existeix fitxer d'estat, False altrament.
        """
        return self.fitxer_estat.exists()

    def carregar(self) -> bool:
        """Carrega l'estat des del fitxer JSON.

        Returns:
            True si s'ha carregat correctament, False si error.
        """
        if not self.existeix():
            print(f"[EstatPipeline] No existeix fitxer d'estat: {self.fitxer_estat}")
            return False

        try:
            contingut = self.fitxer_estat.read_text(encoding="utf-8")
            self._data = EstatPipelineData.model_validate_json(contingut)
            self.sessio_id = self._data.sessio_id
            print(f"[EstatPipeline] Carregat estat: {self.sessio_id}")
            print(f"[EstatPipeline] Fase actual: {self._data.fase_actual}")
            print(f"[EstatPipeline] Chunks completats: {len(self._data.chunks.completats)}/{self._data.chunks.total}")
            return True
        except Exception as e:
            print(f"[EstatPipeline] Error carregant estat: {e}")
            return False

    def guardar(self) -> None:
        """Guarda l'estat actual a disc.

        Es crida automàticament després de cada canvi important.
        """
        # Actualitzar timestamp
        self._data.timestamps["ultima_activitat"] = datetime.now().isoformat()

        # Assegurar que el directori existeix
        self.obra_dir.mkdir(parents=True, exist_ok=True)

        # Guardar JSON
        json_str = self._data.model_dump_json(indent=2)
        self.fitxer_estat.write_text(json_str, encoding="utf-8")

        print(f"[EstatPipeline] Estat guardat: {self.fitxer_estat}")

    def iniciar_fase(self, fase: str) -> None:
        """Marca una fase com a iniciada.

        Args:
            fase: Nom de la fase (ex: "glossari", "chunking", "traduccio").
        """
        self._data.fase_actual = fase
        print(f"[EstatPipeline] Iniciant fase: {fase}")
        self.guardar()

    def completar_fase(self, fase: str) -> None:
        """Marca una fase com a completada.

        Args:
            fase: Nom de la fase completada.
        """
        if fase not in self._data.fases_completades:
            self._data.fases_completades.append(fase)
        print(f"[EstatPipeline] Fase completada: {fase}")
        self.guardar()

    def registrar_chunks(self, chunks: list[str]) -> None:
        """Registra la llista de chunks a processar.

        Args:
            chunks: Llista d'identificadors de chunks.
        """
        self._data.chunks.total = len(chunks)
        self._data.chunks.pendents = chunks.copy()
        self._data.chunks.completats = []
        self._data.chunks.en_curs = None
        print(f"[EstatPipeline] Registrats {len(chunks)} chunks")
        self.guardar()

    def iniciar_chunk(self, chunk_id: str) -> None:
        """Marca un chunk com a en curs.

        Args:
            chunk_id: Identificador del chunk.
        """
        self._data.chunks.en_curs = chunk_id
        if chunk_id in self._data.chunks.pendents:
            self._data.chunks.pendents.remove(chunk_id)
        print(f"[EstatPipeline] Iniciant chunk: {chunk_id}")
        self.guardar()

    def completar_chunk(self, chunk_id: str, qualitat: float) -> None:
        """Marca un chunk com a completat i actualitza mètriques.

        Args:
            chunk_id: Identificador del chunk.
            qualitat: Puntuació de qualitat (0-10).
        """
        # Afegir a completats
        if chunk_id not in self._data.chunks.completats:
            self._data.chunks.completats.append(chunk_id)

        # Netejar en_curs
        if self._data.chunks.en_curs == chunk_id:
            self._data.chunks.en_curs = None

        # Actualitzar mètriques
        n = len(self._data.chunks.completats)
        mitjana_actual = self._data.metriques.qualitat_mitjana
        nova_mitjana = ((mitjana_actual * (n - 1)) + qualitat) / n
        self._data.metriques.qualitat_mitjana = round(nova_mitjana, 2)

        print(f"[EstatPipeline] Chunk completat: {chunk_id} (qualitat: {qualitat:.1f})")
        self.guardar()

    def obtenir_chunks_pendents(self) -> list[str]:
        """Retorna la llista de chunks pendents de processar.

        Inclou el chunk en curs (si n'hi ha) al principi de la llista,
        ja que probablement es va interrompre.

        Returns:
            Llista de chunk_ids pendents.
        """
        pendents = []

        # El chunk en curs va primer (es va interrompre)
        if self._data.chunks.en_curs:
            pendents.append(self._data.chunks.en_curs)

        # Afegir els pendents
        pendents.extend(self._data.chunks.pendents)

        return pendents

    def registrar_error(self, error: str) -> None:
        """Afegeix un error al registre.

        Args:
            error: Descripció de l'error.
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._data.errors.append(f"[{timestamp}] {error}")
        print(f"[EstatPipeline] ERROR: {error}")
        self.guardar()

    def registrar_warning(self, warning: str) -> None:
        """Afegeix un avís al registre.

        Args:
            warning: Descripció de l'avís.
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._data.warnings.append(f"[{timestamp}] {warning}")
        print(f"[EstatPipeline] AVÍS: {warning}")
        self.guardar()

    def actualitzar_temps(self, minuts: float) -> None:
        """Actualitza el temps total de processament.

        Args:
            minuts: Temps en minuts.
        """
        self._data.metriques.temps_total_min = round(minuts, 2)
        self.guardar()

    def resum(self) -> str:
        """Retorna un resum llegible de l'estat actual.

        Returns:
            String amb el resum formatat.
        """
        d = self._data
        chunks_info = d.chunks

        linies = [
            "═" * 60,
            "             ESTAT DEL PIPELINE DE TRADUCCIÓ",
            "═" * 60,
            f"Sessió: {d.sessio_id}",
            f"Obra: {d.obra.titol} ({d.obra.autor})",
            f"Llengua: {d.obra.llengua}",
            "",
            f"Fase actual: {d.fase_actual}",
            f"Fases completades: {', '.join(d.fases_completades) or 'cap'}",
            "",
            "─" * 60,
            "                      CHUNKS",
            "─" * 60,
            f"Total: {chunks_info.total}",
            f"Completats: {len(chunks_info.completats)}",
            f"En curs: {chunks_info.en_curs or 'cap'}",
            f"Pendents: {len(chunks_info.pendents)}",
            "",
            "─" * 60,
            "                     MÈTRIQUES",
            "─" * 60,
            f"Qualitat mitjana: {d.metriques.qualitat_mitjana:.1f}/10",
            f"Temps total: {d.metriques.temps_total_min:.1f} min",
            "",
        ]

        if d.errors:
            linies.append("─" * 60)
            linies.append("                      ERRORS")
            linies.append("─" * 60)
            for e in d.errors[-5:]:  # Últims 5 errors
                linies.append(f"  ✗ {e}")
            linies.append("")

        if d.warnings:
            linies.append("─" * 60)
            linies.append("                      AVISOS")
            linies.append("─" * 60)
            for w in d.warnings[-5:]:  # Últims 5 avisos
                linies.append(f"  ⚠ {w}")
            linies.append("")

        linies.append("═" * 60)
        linies.append(f"Inici: {d.timestamps.get('inici', 'N/A')}")
        linies.append(f"Última activitat: {d.timestamps.get('ultima_activitat', 'N/A')}")
        linies.append("═" * 60)

        return "\n".join(linies)

    @property
    def fase_actual(self) -> str:
        """Retorna la fase actual."""
        return self._data.fase_actual

    @property
    def fases_completades(self) -> list[str]:
        """Retorna les fases completades."""
        return self._data.fases_completades

    @property
    def chunks_completats(self) -> int:
        """Retorna el nombre de chunks completats."""
        return len(self._data.chunks.completats)

    @property
    def chunks_total(self) -> int:
        """Retorna el nombre total de chunks."""
        return self._data.chunks.total

    @property
    def qualitat_mitjana(self) -> float:
        """Retorna la qualitat mitjana."""
        return self._data.metriques.qualitat_mitjana
