"""Sistema de mètriques per al pipeline de traducció."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class MetriquesChunk:
    """Mètriques d'un chunk individual.

    Attributes:
        chunk_id: Identificador del chunk.
        temps_traduccio_s: Temps de traducció en segons.
        temps_revisio_s: Temps de revisió en segons.
        temps_perfeccionament_s: Temps de perfeccionament en segons.
        iteracions_refinament: Nombre d'iteracions de refinament.
        qualitat_inicial: Puntuació de qualitat inicial.
        qualitat_final: Puntuació de qualitat final.
        tokens_input: Tokens d'entrada consumits.
        tokens_output: Tokens de sortida generats.
        errors: Llista d'errors ocorreguts.
    """

    chunk_id: str
    temps_traduccio_s: float = 0.0
    temps_revisio_s: float = 0.0
    temps_perfeccionament_s: float = 0.0
    iteracions_refinament: int = 0
    qualitat_inicial: float | None = None
    qualitat_final: float | None = None
    tokens_input: int = 0
    tokens_output: int = 0
    errors: list[str] = field(default_factory=list)

    def temps_total(self) -> float:
        """Retorna el temps total de processament del chunk."""
        return (
            self.temps_traduccio_s +
            self.temps_revisio_s +
            self.temps_perfeccionament_s
        )

    def millora_qualitat(self) -> float | None:
        """Retorna la millora de qualitat entre inicial i final."""
        if self.qualitat_inicial is None or self.qualitat_final is None:
            return None
        return self.qualitat_final - self.qualitat_inicial


@dataclass
class MetriquesPipeline:
    """Mètriques completes d'una execució del pipeline.

    Attributes:
        sessio_id: Identificador de la sessió.
        obra: Nom de l'obra.
        autor: Nom de l'autor.
        inici: Timestamp d'inici.
        fi: Timestamp de fi.
        chunks: Llista de mètriques per chunk.
        total_tokens_input: Total de tokens d'entrada.
        total_tokens_output: Total de tokens de sortida.
        total_temps_s: Temps total en segons.
        total_cost_eur: Cost total en euros.
    """

    sessio_id: str
    obra: str
    autor: str
    inici: datetime = field(default_factory=datetime.now)
    fi: datetime | None = None
    chunks: list[MetriquesChunk] = field(default_factory=list)

    # Totals
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    total_temps_s: float = 0.0
    total_cost_eur: float = 0.0

    def afegir_chunk(self, metriques: MetriquesChunk) -> None:
        """Afegeix les mètriques d'un chunk i actualitza totals.

        Args:
            metriques: Mètriques del chunk a afegir.
        """
        self.chunks.append(metriques)
        self.total_tokens_input += metriques.tokens_input
        self.total_tokens_output += metriques.tokens_output
        self.total_temps_s += metriques.temps_total()

    def finalitzar(self) -> None:
        """Marca les mètriques com finalitzades."""
        self.fi = datetime.now()

    def resum(self) -> dict[str, Any]:
        """Retorna un resum de les mètriques.

        Returns:
            Diccionari amb el resum de mètriques.
        """
        qualitats = [c.qualitat_final for c in self.chunks if c.qualitat_final is not None]
        iteracions = [c.iteracions_refinament for c in self.chunks]
        errors_totals = sum(len(c.errors) for c in self.chunks)

        durada = str(self.fi - self.inici) if self.fi else "En curs"

        return {
            "sessio_id": self.sessio_id,
            "obra": f"{self.autor} - {self.obra}",
            "durada_total": durada,
            "chunks_processats": len(self.chunks),
            "qualitat_mitjana": sum(qualitats) / len(qualitats) if qualitats else None,
            "qualitat_minima": min(qualitats) if qualitats else None,
            "qualitat_maxima": max(qualitats) if qualitats else None,
            "iteracions_mitjana": sum(iteracions) / len(iteracions) if iteracions else 0,
            "total_tokens": self.total_tokens_input + self.total_tokens_output,
            "total_tokens_input": self.total_tokens_input,
            "total_tokens_output": self.total_tokens_output,
            "cost_estimat_eur": self.total_cost_eur,
            "errors_totals": errors_totals,
            "taxa_exit": (len(self.chunks) - errors_totals) / len(self.chunks) if self.chunks else 0,
        }

    def guardar(self, directori: Path | str = ".cache/metrics") -> Path:
        """Guarda les mètriques a un fitxer JSON.

        Args:
            directori: Directori on guardar les mètriques.

        Returns:
            Path del fitxer guardat.
        """
        directori = Path(directori)
        directori.mkdir(parents=True, exist_ok=True)

        filepath = directori / f"{self.sessio_id}_metrics.json"

        data = {
            "sessio_id": self.sessio_id,
            "obra": self.obra,
            "autor": self.autor,
            "inici": self.inici.isoformat(),
            "fi": self.fi.isoformat() if self.fi else None,
            "chunks": [
                {
                    "chunk_id": c.chunk_id,
                    "temps_traduccio_s": c.temps_traduccio_s,
                    "temps_revisio_s": c.temps_revisio_s,
                    "temps_perfeccionament_s": c.temps_perfeccionament_s,
                    "iteracions_refinament": c.iteracions_refinament,
                    "qualitat_inicial": c.qualitat_inicial,
                    "qualitat_final": c.qualitat_final,
                    "tokens_input": c.tokens_input,
                    "tokens_output": c.tokens_output,
                    "errors": c.errors,
                }
                for c in self.chunks
            ],
            "totals": self.resum(),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return filepath

    @classmethod
    def carregar(cls, filepath: Path | str) -> "MetriquesPipeline":
        """Carrega mètriques d'un fitxer JSON.

        Args:
            filepath: Path del fitxer a carregar.

        Returns:
            Instància de MetriquesPipeline.
        """
        filepath = Path(filepath)

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        metriques = cls(
            sessio_id=data["sessio_id"],
            obra=data["obra"],
            autor=data["autor"],
            inici=datetime.fromisoformat(data["inici"]),
            fi=datetime.fromisoformat(data["fi"]) if data.get("fi") else None,
        )

        for chunk_data in data.get("chunks", []):
            metriques.chunks.append(MetriquesChunk(
                chunk_id=chunk_data["chunk_id"],
                temps_traduccio_s=chunk_data.get("temps_traduccio_s", 0),
                temps_revisio_s=chunk_data.get("temps_revisio_s", 0),
                temps_perfeccionament_s=chunk_data.get("temps_perfeccionament_s", 0),
                iteracions_refinament=chunk_data.get("iteracions_refinament", 0),
                qualitat_inicial=chunk_data.get("qualitat_inicial"),
                qualitat_final=chunk_data.get("qualitat_final"),
                tokens_input=chunk_data.get("tokens_input", 0),
                tokens_output=chunk_data.get("tokens_output", 0),
                errors=chunk_data.get("errors", []),
            ))

        totals = data.get("totals", {})
        metriques.total_tokens_input = totals.get("total_tokens_input", 0)
        metriques.total_tokens_output = totals.get("total_tokens_output", 0)
        metriques.total_cost_eur = totals.get("cost_estimat_eur", 0)

        return metriques


class MetricsCollector:
    """Col·lector de mètriques per sessions múltiples.

    Permet carregar, analitzar i generar informes de múltiples
    execucions del pipeline.
    """

    def __init__(self, directori: Path | str = ".cache/metrics"):
        """Inicialitza el col·lector.

        Args:
            directori: Directori on es guarden les mètriques.
        """
        self.directori = Path(directori)
        self.directori.mkdir(parents=True, exist_ok=True)

    def carregar_totes(self) -> list[dict[str, Any]]:
        """Carrega totes les mètriques guardades.

        Returns:
            Llista de resums de mètriques.
        """
        metriques = []
        for filepath in self.directori.glob("*_metrics.json"):
            try:
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)
                    metriques.append(data.get("totals", data))
            except Exception:
                continue
        return metriques

    def carregar_detall(self, sessio_id: str) -> MetriquesPipeline | None:
        """Carrega les mètriques detallades d'una sessió.

        Args:
            sessio_id: Identificador de la sessió.

        Returns:
            MetriquesPipeline o None si no existeix.
        """
        filepath = self.directori / f"{sessio_id}_metrics.json"
        if not filepath.exists():
            return None
        return MetriquesPipeline.carregar(filepath)

    def informe_global(self) -> str:
        """Genera un informe global de totes les sessions.

        Returns:
            Informe formatat com a string.
        """
        metriques = self.carregar_totes()
        if not metriques:
            return "No hi ha mètriques guardades."

        total_chunks = sum(m.get("chunks_processats", 0) for m in metriques)
        qualitats = [m["qualitat_mitjana"] for m in metriques if m.get("qualitat_mitjana")]
        total_tokens = sum(m.get("total_tokens", 0) for m in metriques)
        total_cost = sum(m.get("cost_estimat_eur", 0) for m in metriques)
        taxa_exit_global = sum(m.get("taxa_exit", 0) for m in metriques) / len(metriques) if metriques else 0

        lines = [
            "═══ INFORME GLOBAL DE MÈTRIQUES ═══",
            "",
            f"Sessions totals: {len(metriques)}",
            f"Chunks processats: {total_chunks}",
            "",
            "─── Qualitat ───",
            f"Qualitat mitjana global: {sum(qualitats)/len(qualitats):.2f}" if qualitats else "N/A",
            f"Taxa d'èxit global: {taxa_exit_global*100:.1f}%",
            "",
            "─── Recursos ───",
            f"Tokens totals: {total_tokens:,}",
            f"Cost total estimat: €{total_cost:.4f}",
            "",
            "═" * 35,
        ]

        return "\n".join(lines)

    def informe_sessio(self, sessio_id: str) -> str:
        """Genera un informe detallat d'una sessió.

        Args:
            sessio_id: Identificador de la sessió.

        Returns:
            Informe formatat com a string.
        """
        metriques = self.carregar_detall(sessio_id)
        if not metriques:
            return f"No s'han trobat mètriques per a la sessió '{sessio_id}'"

        resum = metriques.resum()

        lines = [
            f"═══ INFORME SESSIÓ: {sessio_id} ═══",
            "",
            f"Obra: {resum['obra']}",
            f"Durada: {resum['durada_total']}",
            "",
            "─── Chunks ───",
            f"Processats: {resum['chunks_processats']}",
            f"Iteracions mitjana: {resum['iteracions_mitjana']:.1f}",
            "",
            "─── Qualitat ───",
            f"Mitjana: {resum['qualitat_mitjana']:.2f}" if resum['qualitat_mitjana'] else "N/A",
            f"Mínima: {resum['qualitat_minima']:.2f}" if resum['qualitat_minima'] else "N/A",
            f"Màxima: {resum['qualitat_maxima']:.2f}" if resum['qualitat_maxima'] else "N/A",
            f"Taxa èxit: {resum['taxa_exit']*100:.1f}%",
            "",
            "─── Recursos ───",
            f"Tokens entrada: {resum['total_tokens_input']:,}",
            f"Tokens sortida: {resum['total_tokens_output']:,}",
            f"Cost estimat: €{resum['cost_estimat_eur']:.4f}",
            "",
        ]

        # Detalls per chunk
        if metriques.chunks:
            lines.append("─── Detall per chunk ───")
            for chunk in metriques.chunks:
                status = "✓" if not chunk.errors else "✗"
                qual = f"{chunk.qualitat_final:.1f}" if chunk.qualitat_final else "N/A"
                lines.append(f"  {status} Chunk {chunk.chunk_id}: {qual}/10 ({chunk.iteracions_refinament} iter)")

        lines.append("")
        lines.append("═" * 40)

        return "\n".join(lines)

    def comparar_sessions(self, sessio_ids: list[str]) -> str:
        """Compara múltiples sessions.

        Args:
            sessio_ids: Llista d'identificadors de sessions a comparar.

        Returns:
            Taula comparativa formatada.
        """
        lines = ["═══ COMPARACIÓ DE SESSIONS ═══", ""]

        # Capçalera
        header = f"{'Sessió':<20} {'Chunks':>8} {'Qualitat':>10} {'Taxa':>8} {'Tokens':>12}"
        lines.append(header)
        lines.append("─" * len(header))

        for sessio_id in sessio_ids:
            metriques = self.carregar_detall(sessio_id)
            if not metriques:
                lines.append(f"{sessio_id:<20} {'N/A':>8} {'N/A':>10} {'N/A':>8} {'N/A':>12}")
                continue

            resum = metriques.resum()
            qual = f"{resum['qualitat_mitjana']:.1f}" if resum['qualitat_mitjana'] else "N/A"
            taxa = f"{resum['taxa_exit']*100:.0f}%"
            tokens = f"{resum['total_tokens']:,}"

            lines.append(f"{sessio_id[:20]:<20} {resum['chunks_processats']:>8} {qual:>10} {taxa:>8} {tokens:>12}")

        lines.append("")
        lines.append("═" * len(header))

        return "\n".join(lines)

    def eliminar_metriques(self, sessio_id: str) -> bool:
        """Elimina les mètriques d'una sessió.

        Args:
            sessio_id: Identificador de la sessió.

        Returns:
            True si s'ha eliminat, False si no existia.
        """
        filepath = self.directori / f"{sessio_id}_metrics.json"
        if filepath.exists():
            filepath.unlink()
            return True
        return False
