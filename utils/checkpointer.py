"""Sistema de checkpointing per recuperació d'errors del pipeline."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class ChunkCheckpoint(BaseModel):
    """Checkpoint d'un chunk individual."""

    chunk_id: str
    estat: Literal[
        "pendent",
        "traductor",
        "revisor",
        "perfeccionament",
        "anotador",
        "completat",
        "error",
    ] = "pendent"
    text_original: str
    text_traduit: str | None = None
    text_revisat: str | None = None
    text_perfeccionat: str | None = None
    text_anotat: str | None = None
    notes: list[dict] = Field(default_factory=list)
    iteracions_revisor: int = 0
    iteracions_perfeccionament: int = 0
    qualitat: float | None = None
    error_message: str | None = None
    metadata: dict = Field(default_factory=dict)
    timestamp_inici: datetime | None = None
    timestamp_fi: datetime | None = None


class PipelineCheckpoint(BaseModel):
    """Checkpoint complet del pipeline."""

    sessio_id: str
    obra: str
    autor: str
    llengua_origen: str = "llati"
    genere: str = "narrativa"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    fase_actual: Literal[
        "inicialitzant",
        "brief",
        "pescador",
        "costos",
        "investigador",
        "glossarista",
        "traduccio",
        "fusio",
        "introduccio",
        "aprovacio",
        "publicacio",
        "completat",
        "error",
    ] = "inicialitzant"

    # Fase inicial
    brief_editorial: dict | None = None
    text_original_complet: str | None = None
    cost_estimat: float | None = None
    context_investigador: dict | None = None
    glossari: dict | None = None

    # Fase traducció
    chunks: list[ChunkCheckpoint] = Field(default_factory=list)
    chunk_actual: int = 0

    # Fase final
    text_fusionat: str | None = None
    introduccio: str | None = None
    aprovat: bool | None = None

    # Fase publicació
    portada_path: str | None = None
    retrat_path: str | None = None
    epub_path: str | None = None
    pdf_path: str | None = None
    html_path: str | None = None

    # Estadístiques
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    total_cost_eur: float = 0.0
    total_temps_segons: float = 0.0
    errors_count: int = 0


class Checkpointer:
    """Gestor de checkpoints per recuperació d'errors.

    Permet guardar l'estat del pipeline a disc i reprendre'l
    en cas d'error o interrupció.
    """

    def __init__(self, checkpoint_dir: Path | str | None = None):
        """Inicialitza el checkpointer.

        Args:
            checkpoint_dir: Directori on guardar els checkpoints.
                          Per defecte: .cache/pipeline/checkpoints
        """
        if checkpoint_dir is None:
            self.checkpoint_dir = Path(".cache/pipeline/checkpoints")
        else:
            self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint: PipelineCheckpoint | None = None

    def _get_filepath(self, sessio_id: str) -> Path:
        """Retorna el path del fitxer de checkpoint."""
        return self.checkpoint_dir / f"{sessio_id}.checkpoint.json"

    def iniciar(
        self,
        sessio_id: str,
        obra: str,
        autor: str,
        llengua_origen: str = "llati",
        genere: str = "narrativa",
    ) -> PipelineCheckpoint:
        """Inicia un nou checkpoint.

        Args:
            sessio_id: Identificador únic de la sessió.
            obra: Nom de l'obra.
            autor: Nom de l'autor.
            llengua_origen: Llengua d'origen del text.
            genere: Gènere literari.

        Returns:
            Nou PipelineCheckpoint inicialitzat.
        """
        self.checkpoint = PipelineCheckpoint(
            sessio_id=sessio_id,
            obra=obra,
            autor=autor,
            llengua_origen=llengua_origen,
            genere=genere,
            fase_actual="inicialitzant",
        )
        self._save()
        return self.checkpoint

    def carregar(self, sessio_id: str) -> PipelineCheckpoint | None:
        """Carrega un checkpoint existent.

        Args:
            sessio_id: Identificador de la sessió a carregar.

        Returns:
            PipelineCheckpoint carregat o None si no existeix.
        """
        filepath = self._get_filepath(sessio_id)
        if not filepath.exists():
            return None

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Convertir strings de datetime a objectes datetime
        for field in ["created_at", "updated_at"]:
            if field in data and isinstance(data[field], str):
                data[field] = datetime.fromisoformat(data[field])

        for chunk in data.get("chunks", []):
            for field in ["timestamp_inici", "timestamp_fi"]:
                if field in chunk and chunk[field] and isinstance(chunk[field], str):
                    chunk[field] = datetime.fromisoformat(chunk[field])

        self.checkpoint = PipelineCheckpoint(**data)
        return self.checkpoint

    def existeix(self, sessio_id: str) -> bool:
        """Comprova si existeix un checkpoint.

        Args:
            sessio_id: Identificador de la sessió.

        Returns:
            True si existeix el checkpoint.
        """
        return self._get_filepath(sessio_id).exists()

    def llistar_sessions(self) -> list[str]:
        """Llista tots els checkpoints disponibles.

        Returns:
            Llista d'identificadors de sessió.
        """
        return [
            f.stem.replace(".checkpoint", "")
            for f in self.checkpoint_dir.glob("*.checkpoint.json")
        ]

    def llistar_incomplets(self) -> list[dict[str, Any]]:
        """Llista checkpoints incomplets que es poden reprendre.

        Returns:
            Llista de diccionaris amb info dels checkpoints incomplets.
        """
        incomplets = []
        for filepath in self.checkpoint_dir.glob("*.checkpoint.json"):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("fase_actual") not in ["completat", "error"]:
                chunks_completats = sum(
                    1 for c in data.get("chunks", []) if c.get("estat") == "completat"
                )
                incomplets.append({
                    "sessio_id": data["sessio_id"],
                    "obra": data["obra"],
                    "autor": data["autor"],
                    "fase": data["fase_actual"],
                    "chunks_completats": chunks_completats,
                    "chunks_total": len(data.get("chunks", [])),
                    "updated_at": data["updated_at"],
                })
        return incomplets

    def _save(self) -> None:
        """Guarda el checkpoint actual a disc."""
        if not self.checkpoint:
            return

        self.checkpoint.updated_at = datetime.now()
        filepath = self._get_filepath(self.checkpoint.sessio_id)

        # Convertir a diccionari serialitzable
        data = self.checkpoint.model_dump(mode="json")

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    # === Mètodes de fase inicial ===

    def guardar_brief(self, brief: dict) -> None:
        """Guarda el brief editorial."""
        if self.checkpoint:
            self.checkpoint.brief_editorial = brief
            self.checkpoint.fase_actual = "brief"
            self._save()

    def guardar_text_original(self, text: str) -> None:
        """Guarda el text original complet."""
        if self.checkpoint:
            self.checkpoint.text_original_complet = text
            self.checkpoint.fase_actual = "pescador"
            self._save()

    def guardar_cost_estimat(self, cost: float) -> None:
        """Guarda el cost estimat."""
        if self.checkpoint:
            self.checkpoint.cost_estimat = cost
            self.checkpoint.fase_actual = "costos"
            self._save()

    def guardar_context(self, context: dict) -> None:
        """Guarda el context de l'investigador."""
        if self.checkpoint:
            self.checkpoint.context_investigador = context
            self.checkpoint.fase_actual = "investigador"
            self._save()

    def guardar_glossari(self, glossari: dict) -> None:
        """Guarda el glossari i passa a fase de traducció."""
        if self.checkpoint:
            self.checkpoint.glossari = glossari
            self.checkpoint.fase_actual = "traduccio"
            self._save()

    # === Mètodes de fase traducció ===

    def iniciar_chunks(self, chunks_originals: list[str]) -> None:
        """Inicialitza els chunks per traduir.

        Args:
            chunks_originals: Llista de textos originals per cada chunk.
        """
        if self.checkpoint:
            self.checkpoint.chunks = [
                ChunkCheckpoint(
                    chunk_id=str(i + 1),
                    estat="pendent",
                    text_original=text,
                )
                for i, text in enumerate(chunks_originals)
            ]
            self.checkpoint.fase_actual = "traduccio"
            self._save()

    def actualitzar_chunk(self, chunk_id: str, **kwargs: Any) -> None:
        """Actualitza l'estat d'un chunk.

        Args:
            chunk_id: Identificador del chunk.
            **kwargs: Camps a actualitzar (estat, text_traduit, etc.)
        """
        if not self.checkpoint:
            return

        for chunk in self.checkpoint.chunks:
            if chunk.chunk_id == chunk_id:
                for key, value in kwargs.items():
                    if hasattr(chunk, key):
                        setattr(chunk, key, value)
                break
        self._save()

    def chunk_inici(self, chunk_id: str) -> None:
        """Marca l'inici del processament d'un chunk."""
        self.actualitzar_chunk(
            chunk_id,
            estat="traductor",
            timestamp_inici=datetime.now(),
        )

    def chunk_completat(self, chunk_id: str, qualitat: float | None = None) -> None:
        """Marca un chunk com completat.

        Args:
            chunk_id: Identificador del chunk.
            qualitat: Puntuació de qualitat (opcional).
        """
        if self.checkpoint:
            self.actualitzar_chunk(
                chunk_id,
                estat="completat",
                qualitat=qualitat,
                timestamp_fi=datetime.now(),
            )
            self.checkpoint.chunk_actual = int(chunk_id)
            self._save()

    def chunk_error(self, chunk_id: str, error_message: str) -> None:
        """Marca un chunk amb error.

        Args:
            chunk_id: Identificador del chunk.
            error_message: Missatge d'error.
        """
        if self.checkpoint:
            self.actualitzar_chunk(
                chunk_id,
                estat="error",
                error_message=error_message,
                timestamp_fi=datetime.now(),
            )
            self.checkpoint.errors_count += 1
            self._save()

    def obtenir_chunks_pendents(self) -> list[ChunkCheckpoint]:
        """Retorna chunks no completats.

        Returns:
            Llista de chunks pendents de processar.
        """
        if not self.checkpoint:
            return []
        return [c for c in self.checkpoint.chunks if c.estat != "completat"]

    def obtenir_ultim_chunk_completat(self) -> ChunkCheckpoint | None:
        """Retorna l'últim chunk completat.

        Returns:
            Últim chunk completat o None.
        """
        if not self.checkpoint:
            return None
        completats = [c for c in self.checkpoint.chunks if c.estat == "completat"]
        return completats[-1] if completats else None

    # === Mètodes de fase final ===

    def guardar_fusio(self, text: str) -> None:
        """Guarda el text fusionat de tots els chunks."""
        if self.checkpoint:
            self.checkpoint.text_fusionat = text
            self.checkpoint.fase_actual = "fusio"
            self._save()

    def guardar_introduccio(self, text: str) -> None:
        """Guarda la introducció generada."""
        if self.checkpoint:
            self.checkpoint.introduccio = text
            self.checkpoint.fase_actual = "introduccio"
            self._save()

    def guardar_aprovacio(self, aprovat: bool) -> None:
        """Guarda el resultat de l'aprovació editorial."""
        if self.checkpoint:
            self.checkpoint.aprovat = aprovat
            if aprovat:
                self.checkpoint.fase_actual = "publicacio"
            else:
                self.checkpoint.fase_actual = "error"
            self._save()

    # === Mètodes de fase publicació ===

    def guardar_portada(self, path: str) -> None:
        """Guarda el path de la portada generada."""
        if self.checkpoint:
            self.checkpoint.portada_path = path
            self._save()

    def guardar_retrat(self, path: str) -> None:
        """Guarda el path del retrat d'autor generat."""
        if self.checkpoint:
            self.checkpoint.retrat_path = path
            self._save()

    def guardar_publicacio(
        self,
        epub: str | None = None,
        pdf: str | None = None,
        html: str | None = None,
    ) -> None:
        """Guarda els paths dels fitxers publicats."""
        if self.checkpoint:
            if epub:
                self.checkpoint.epub_path = epub
            if pdf:
                self.checkpoint.pdf_path = pdf
            if html:
                self.checkpoint.html_path = html
            self._save()

    # === Mètodes d'estadístiques ===

    def actualitzar_estadistiques(
        self,
        tokens_input: int = 0,
        tokens_output: int = 0,
        cost_eur: float = 0.0,
        temps_segons: float = 0.0,
    ) -> None:
        """Actualitza les estadístiques acumulades.

        Args:
            tokens_input: Tokens d'entrada a afegir.
            tokens_output: Tokens de sortida a afegir.
            cost_eur: Cost en euros a afegir.
            temps_segons: Temps en segons a afegir.
        """
        if self.checkpoint:
            self.checkpoint.total_tokens_input += tokens_input
            self.checkpoint.total_tokens_output += tokens_output
            self.checkpoint.total_cost_eur += cost_eur
            self.checkpoint.total_temps_segons += temps_segons
            self._save()

    # === Mètodes de finalització ===

    def finalitzar(self) -> None:
        """Marca el pipeline com completat."""
        if self.checkpoint:
            self.checkpoint.fase_actual = "completat"
            self._save()

    def marcar_error(self, error_message: str | None = None) -> None:
        """Marca el pipeline amb error global."""
        if self.checkpoint:
            self.checkpoint.fase_actual = "error"
            if error_message:
                self.checkpoint.errors_count += 1
            self._save()

    def eliminar(self, sessio_id: str) -> bool:
        """Elimina un checkpoint.

        Args:
            sessio_id: Identificador de la sessió a eliminar.

        Returns:
            True si s'ha eliminat, False si no existia.
        """
        filepath = self._get_filepath(sessio_id)
        if filepath.exists():
            filepath.unlink()
            return True
        return False

    def obtenir_resum(self) -> dict[str, Any] | None:
        """Retorna un resum de l'estat actual del checkpoint.

        Returns:
            Diccionari amb el resum o None si no hi ha checkpoint.
        """
        if not self.checkpoint:
            return None

        chunks_completats = sum(
            1 for c in self.checkpoint.chunks if c.estat == "completat"
        )
        chunks_error = sum(1 for c in self.checkpoint.chunks if c.estat == "error")
        qualitats = [
            c.qualitat for c in self.checkpoint.chunks
            if c.qualitat is not None
        ]

        return {
            "sessio_id": self.checkpoint.sessio_id,
            "obra": self.checkpoint.obra,
            "autor": self.checkpoint.autor,
            "fase_actual": self.checkpoint.fase_actual,
            "chunks_total": len(self.checkpoint.chunks),
            "chunks_completats": chunks_completats,
            "chunks_error": chunks_error,
            "chunks_pendents": len(self.checkpoint.chunks) - chunks_completats - chunks_error,
            "qualitat_mitjana": sum(qualitats) / len(qualitats) if qualitats else None,
            "total_tokens": self.checkpoint.total_tokens_input + self.checkpoint.total_tokens_output,
            "total_cost_eur": self.checkpoint.total_cost_eur,
            "total_temps_segons": self.checkpoint.total_temps_segons,
            "errors_count": self.checkpoint.errors_count,
            "created_at": self.checkpoint.created_at.isoformat(),
            "updated_at": self.checkpoint.updated_at.isoformat(),
        }
