"""Models de dades per als agents de debugging.

Defineix les estructures de dades per a BugReport i BugFix,
utilitzades en el flux TDD de reproducció i correcció de bugs.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal


@dataclass
class BugReport:
    """Informe d'un bug reproduït amb test que falla.

    Generat per BugReproducerAgent després d'analitzar un bug
    i crear un test pytest que el demostra.

    Attributes:
        descripcio: Descripció original del bug.
        fitxer_afectat: Camí al fitxer on es troba el bug.
        funcio_afectada: Nom de la funció o mètode amb el bug.
        test_code: Codi pytest complet que falla i demostra el bug.
        test_file: Camí on s'ha guardat el test (opcional).
        passos_reproduccio: Llista de passos per reproduir el bug manualment.
        comportament_esperat: Què hauria de fer el codi.
        comportament_actual: Què fa realment el codi (incorrecte).
        severitat: Nivell de gravetat del bug.
        context_adicional: Informació extra rellevant per al diagnòstic.
        data_creacio: Quan s'ha creat l'informe.
    """

    descripcio: str
    fitxer_afectat: Path
    funcio_afectada: str
    test_code: str
    passos_reproduccio: list[str]
    comportament_esperat: str
    comportament_actual: str
    severitat: Literal["critica", "alta", "mitjana", "baixa"] = "mitjana"
    test_file: Path | None = None
    context_adicional: str = ""
    data_creacio: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Converteix paths a objectes Path si són strings."""
        if isinstance(self.fitxer_afectat, str):
            self.fitxer_afectat = Path(self.fitxer_afectat)
        if isinstance(self.test_file, str):
            self.test_file = Path(self.test_file)

    def to_dict(self) -> dict:
        """Converteix a diccionari per serialització."""
        return {
            "descripcio": self.descripcio,
            "fitxer_afectat": str(self.fitxer_afectat),
            "funcio_afectada": self.funcio_afectada,
            "test_code": self.test_code,
            "test_file": str(self.test_file) if self.test_file else None,
            "passos_reproduccio": self.passos_reproduccio,
            "comportament_esperat": self.comportament_esperat,
            "comportament_actual": self.comportament_actual,
            "severitat": self.severitat,
            "context_adicional": self.context_adicional,
            "data_creacio": self.data_creacio.isoformat(),
        }


@dataclass
class BugFix:
    """Resultat d'intentar arreglar un bug.

    Generat per BugFixerAgent després d'analitzar el BugReport
    i aplicar canvis al codi.

    Attributes:
        bug_report: L'informe del bug que s'ha intentat arreglar.
        fitxer_modificat: Camí al fitxer que s'ha modificat.
        diff: Canvis aplicats en format diff unificat.
        codi_original: Codi abans del canvi (la part afectada).
        codi_nou: Codi després del canvi.
        explicacio: Descripció del canvi i per què soluciona el bug.
        test_passa: Si el test ara passa després del canvi.
        intents: Nombre d'intents necessaris per trobar la solució.
        error_test: Missatge d'error si el test encara falla.
        data_fix: Quan s'ha aplicat el fix.
    """

    bug_report: BugReport
    fitxer_modificat: Path
    diff: str
    codi_original: str
    codi_nou: str
    explicacio: str
    test_passa: bool
    intents: int = 1
    error_test: str = ""
    data_fix: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Converteix paths a objectes Path si són strings."""
        if isinstance(self.fitxer_modificat, str):
            self.fitxer_modificat = Path(self.fitxer_modificat)

    def to_dict(self) -> dict:
        """Converteix a diccionari per serialització."""
        return {
            "bug_report": self.bug_report.to_dict(),
            "fitxer_modificat": str(self.fitxer_modificat),
            "diff": self.diff,
            "codi_original": self.codi_original,
            "codi_nou": self.codi_nou,
            "explicacio": self.explicacio,
            "test_passa": self.test_passa,
            "intents": self.intents,
            "error_test": self.error_test,
            "data_fix": self.data_fix.isoformat(),
        }

    @property
    def exit(self) -> bool:
        """Indica si el fix ha estat exitós."""
        return self.test_passa


@dataclass
class DebugResult:
    """Resultat complet del procés de debugging.

    Agrupa el BugReport i el BugFix (si s'ha intentat arreglar).

    Attributes:
        bug_report: Informe del bug reproduït.
        bug_fix: Resultat de l'intent d'arreglar (None si només reproducció).
        dry_run: Si s'ha executat en mode només reproducció.
        temps_total: Temps total del procés en segons.
    """

    bug_report: BugReport | None
    bug_fix: BugFix | None = None
    dry_run: bool = False
    temps_total: float = 0.0

    @property
    def exit(self) -> bool:
        """Indica si el debugging ha estat completament exitós."""
        if self.dry_run:
            return self.bug_report is not None
        return self.bug_fix is not None and self.bug_fix.test_passa

    def resum(self) -> str:
        """Genera un resum del resultat."""
        lines = ["=" * 60, "  RESULTAT DE DEBUGGING", "=" * 60]

        if self.bug_report:
            lines.extend([
                f"Bug: {self.bug_report.descripcio[:50]}...",
                f"Fitxer: {self.bug_report.fitxer_afectat}",
                f"Funció: {self.bug_report.funcio_afectada}",
                f"Severitat: {self.bug_report.severitat}",
            ])

        if self.dry_run:
            lines.append("\n[Mode dry-run: només reproducció]")
        elif self.bug_fix:
            lines.extend([
                "",
                f"Fix aplicat: {'Sí' if self.bug_fix.test_passa else 'No'}",
                f"Intents: {self.bug_fix.intents}",
                f"Fitxer modificat: {self.bug_fix.fitxer_modificat}",
            ])

        lines.extend([
            "",
            f"Temps total: {self.temps_total:.1f}s",
            f"Resultat: {'ÈXIT' if self.exit else 'FALLADA'}",
            "=" * 60,
        ])

        return "\n".join(lines)
