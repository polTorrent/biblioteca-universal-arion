"""Agent per arreglar bugs basant-se en tests que fallen.

BugFixerAgent rep un BugReport amb un test que falla i proposa
el mínim canvi necessari per fer passar el test.
"""

import difflib
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from agents.base_agent import AgentConfig, BaseAgent
from agents.debug.models import BugFix, BugReport


# System prompt per l'agent corrector de bugs
BUG_FIXER_SYSTEM_PROMPT = """Ets un desenvolupador expert en debugging i refactoring. Reps:
- Un test pytest que FALLA
- El codi font actual on es troba el bug

La teva missió és:
1. ANALITZAR per què el test falla exactament
2. IDENTIFICAR la causa arrel del problema (no només els símptomes)
3. PROPOSAR el MÍNIM canvi necessari per fer passar el test
4. EXPLICAR clarament què has canviat i per què

Regles ESTRICTES:
- NO canviïs el test - és el contracte que has de complir
- NO afegeixis funcionalitats extres no requerides
- Fes el MÍNIM canvi possible per solucionar el bug
- Manté la compatibilitat amb la resta del codi
- Escriu comentaris en CATALÀ si n'afegeixes
- Preserva l'estil de codi existent

Format de sortida OBLIGATORI (usa exactament aquestes etiquetes XML):

<analisi>
Explicació detallada de per què el test falla i quina és la causa arrel.
</analisi>

<fitxer>path/al/fitxer.py</fitxer>

<linia_inici>número de línia on comença el bloc a modificar</linia_inici>

<linia_fi>número de línia on acaba el bloc a modificar</linia_fi>

<codi_original>
El codi EXACTE que cal substituir (amb context suficient per ser únic)
</codi_original>

<codi_nou>
El codi nou que substitueix l'anterior
</codi_nou>

<explicacio>
Què has canviat i per què això soluciona el bug.
</explicacio>
"""


class BugFixerAgent(BaseAgent):
    """Agent especialitzat en arreglar bugs basant-se en tests.

    Analitza un BugReport amb un test que falla, proposa canvis
    mínims al codi, i verifica que el test passi després dels canvis.

    Example:
        >>> agent = BugFixerAgent()
        >>> fix = agent.fix(bug_report)
        >>> if fix.test_passa:
        ...     print("Bug arreglat!")
    """

    agent_name = "BugFixer"

    # Màxim d'intents per arreglar un bug
    MAX_INTENTS = 3

    def __init__(
        self,
        config: AgentConfig | None = None,
        base_dir: Path | None = None,
        max_intents: int = 3,
    ) -> None:
        """Inicialitza l'agent.

        Args:
            config: Configuració de l'agent.
            base_dir: Directori base del projecte.
            max_intents: Màxim d'intents per arreglar el bug.
        """
        super().__init__(config=config)
        self.base_dir = base_dir or Path.cwd()
        self.max_intents = max_intents

    @property
    def system_prompt(self) -> str:
        """Retorna el system prompt de l'agent."""
        return BUG_FIXER_SYSTEM_PROMPT

    def _read_source_file(self, fitxer: Path) -> tuple[str, list[str]]:
        """Llegeix un fitxer font i retorna contingut i línies.

        Args:
            fitxer: Camí al fitxer.

        Returns:
            Tupla (contingut complet, llista de línies).
        """
        path = self.base_dir / fitxer if not fitxer.is_absolute() else fitxer
        content = path.read_text(encoding="utf-8")
        lines = content.splitlines(keepends=True)
        return content, lines

    def _run_test(self, test_file: Path, test_code: str | None = None) -> tuple[bool, str]:
        """Executa un test pytest i retorna el resultat.

        Args:
            test_file: Camí al fitxer de test.
            test_code: Si es proporciona, es crea un fitxer temporal.

        Returns:
            Tupla (test_passa, output/error).
        """
        # Si tenim codi però no fitxer, crear temporal
        if test_code and (not test_file or not test_file.exists()):
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".py",
                delete=False,
                encoding="utf-8",
            ) as f:
                f.write(test_code)
                test_file = Path(f.name)

        try:
            # Usar sys.executable per assegurar el Python correcte
            import sys
            python_cmd = sys.executable
            result = subprocess.run(
                [python_cmd, "-m", "pytest", str(test_file), "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.base_dir),
            )
            test_passa = result.returncode == 0
            output = result.stdout + result.stderr
            return test_passa, output
        except subprocess.TimeoutExpired:
            return False, "Test timeout (>30s)"
        except Exception as e:
            return False, f"Error executant test: {e}"

    def _parse_response(self, response: str) -> dict[str, Any]:
        """Parseja la resposta de l'agent.

        Args:
            response: Resposta textual de l'agent.

        Returns:
            Diccionari amb els camps extrets.
        """
        result: dict[str, Any] = {}

        patterns = {
            "analisi": r"<analisi>(.*?)</analisi>",
            "fitxer": r"<fitxer>(.*?)</fitxer>",
            "linia_inici": r"<linia_inici>(.*?)</linia_inici>",
            "linia_fi": r"<linia_fi>(.*?)</linia_fi>",
            "codi_original": r"<codi_original>(.*?)</codi_original>",
            "codi_nou": r"<codi_nou>(.*?)</codi_nou>",
            "explicacio": r"<explicacio>(.*?)</explicacio>",
        }

        for camp, pattern in patterns.items():
            match = re.search(pattern, response, re.DOTALL)
            if match:
                value = match.group(1).strip()
                # Treure blocs de codi markdown si existeixen
                if camp in ("codi_original", "codi_nou"):
                    value = re.sub(r"^```\w*\n?", "", value)
                    value = re.sub(r"\n?```$", "", value)
                result[camp] = value

        return result

    def _apply_fix(self, fitxer: Path, codi_original: str, codi_nou: str) -> tuple[bool, str]:
        """Aplica un canvi a un fitxer.

        Args:
            fitxer: Camí al fitxer a modificar.
            codi_original: Codi a substituir.
            codi_nou: Codi nou.

        Returns:
            Tupla (èxit, missatge).
        """
        path = self.base_dir / fitxer if not fitxer.is_absolute() else fitxer

        try:
            content = path.read_text(encoding="utf-8")

            if codi_original not in content:
                # Intentar amb normalització d'espais
                content_normalized = re.sub(r'\s+', ' ', content)
                original_normalized = re.sub(r'\s+', ' ', codi_original)

                if original_normalized not in content_normalized:
                    return False, "No s'ha trobat el codi original al fitxer"

                # Reconstruir la substitució
                # Trobar posició aproximada
                idx = content_normalized.find(original_normalized)
                if idx == -1:
                    return False, "No s'ha pogut localitzar el codi"

            # Fer la substitució
            new_content = content.replace(codi_original, codi_nou, 1)

            if new_content == content:
                return False, "No s'ha fet cap canvi"

            # Guardar backup
            backup_path = path.with_suffix(path.suffix + ".backup")
            backup_path.write_text(content, encoding="utf-8")

            # Aplicar canvi
            path.write_text(new_content, encoding="utf-8")

            return True, f"Canvi aplicat. Backup a {backup_path}"

        except Exception as e:
            return False, f"Error aplicant canvi: {e}"

    def _revert_fix(self, fitxer: Path) -> bool:
        """Reverteix un canvi des del backup.

        Args:
            fitxer: Camí al fitxer modificat.

        Returns:
            True si s'ha revertit correctament.
        """
        path = self.base_dir / fitxer if not fitxer.is_absolute() else fitxer
        backup_path = path.with_suffix(path.suffix + ".backup")

        try:
            if backup_path.exists():
                content = backup_path.read_text(encoding="utf-8")
                path.write_text(content, encoding="utf-8")
                backup_path.unlink()
                return True
            return False
        except Exception:
            return False

    def _generate_diff(self, original: str, nou: str, fitxer: str) -> str:
        """Genera un diff unificat entre dues versions.

        Args:
            original: Codi original.
            nou: Codi nou.
            fitxer: Nom del fitxer per al diff.

        Returns:
            Diff en format unificat.
        """
        original_lines = original.splitlines(keepends=True)
        nou_lines = nou.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            nou_lines,
            fromfile=f"a/{fitxer}",
            tofile=f"b/{fitxer}",
        )

        return "".join(diff)

    def fix(
        self,
        bug_report: BugReport,
        aplicar_canvis: bool = True,
        revertir_si_falla: bool = True,
    ) -> BugFix:
        """Intenta arreglar un bug basat en el report.

        Args:
            bug_report: Informe del bug amb el test que falla.
            aplicar_canvis: Si s'han d'aplicar els canvis al fitxer.
            revertir_si_falla: Si s'ha de revertir si el test no passa.

        Returns:
            BugFix amb el resultat de l'intent.
        """
        self.log_info(f"Intentant arreglar: {bug_report.funcio_afectada}")

        # Llegir codi font actual
        try:
            source_content, _ = self._read_source_file(bug_report.fitxer_afectat)
        except FileNotFoundError:
            return BugFix(
                bug_report=bug_report,
                fitxer_modificat=bug_report.fitxer_afectat,
                diff="",
                codi_original="",
                codi_nou="",
                explicacio="No s'ha trobat el fitxer font",
                test_passa=False,
                intents=0,
                error_test="FileNotFoundError",
            )

        # Verificar que el test falla inicialment
        test_passa_inicial, output_inicial = self._run_test(
            bug_report.test_file,
            bug_report.test_code,
        )

        if test_passa_inicial:
            self.log_warning("El test ja passa! El bug potser ja està arreglat.")
            return BugFix(
                bug_report=bug_report,
                fitxer_modificat=bug_report.fitxer_afectat,
                diff="",
                codi_original="",
                codi_nou="",
                explicacio="El test ja passava abans d'aplicar cap canvi",
                test_passa=True,
                intents=0,
            )

        # Iterar fins que el test passi o s'esgotin els intents
        last_error = output_inicial
        codi_original = ""
        codi_nou = ""
        explicacio = ""

        for intent in range(1, self.max_intents + 1):
            self.log_info(f"Intent {intent}/{self.max_intents}")

            # Construir prompt amb context
            prompt = f"""## Bug Report

Descripció: {bug_report.descripcio}
Fitxer: {bug_report.fitxer_afectat}
Funció: {bug_report.funcio_afectada}
Comportament esperat: {bug_report.comportament_esperat}
Comportament actual: {bug_report.comportament_actual}

## Test que Falla

```python
{bug_report.test_code}
```

## Error del Test

```
{last_error}
```

## Codi Font Actual

```python
{source_content}
```

## Tasca

Proposa el MÍNIM canvi per fer passar el test.
{"Nota: Intent anterior ha fallat, prova una aproximació diferent." if intent > 1 else ""}
"""

            # Cridar a l'agent
            response = self.process(prompt)
            parsed = self._parse_response(response.content)

            # Validar resposta
            if not parsed.get("codi_original") or not parsed.get("codi_nou"):
                self.log_warning("Resposta incompleta de l'agent")
                continue

            codi_original = parsed["codi_original"]
            codi_nou = parsed["codi_nou"]
            explicacio = parsed.get("explicacio", "")

            if not aplicar_canvis:
                # Mode dry-run: només retornar la proposta
                return BugFix(
                    bug_report=bug_report,
                    fitxer_modificat=bug_report.fitxer_afectat,
                    diff=self._generate_diff(codi_original, codi_nou, str(bug_report.fitxer_afectat)),
                    codi_original=codi_original,
                    codi_nou=codi_nou,
                    explicacio=explicacio,
                    test_passa=False,  # No verificat
                    intents=intent,
                )

            # Aplicar canvi
            exit_aplicar, msg_aplicar = self._apply_fix(
                bug_report.fitxer_afectat,
                codi_original,
                codi_nou,
            )

            if not exit_aplicar:
                self.log_warning(f"No s'ha pogut aplicar el canvi: {msg_aplicar}")
                last_error = msg_aplicar
                continue

            # Executar test
            test_passa, output_test = self._run_test(
                bug_report.test_file,
                bug_report.test_code,
            )

            if test_passa:
                self.log_info(f"Test passa després de l'intent {intent}")
                # Eliminar backup
                backup_path = (self.base_dir / bug_report.fitxer_afectat).with_suffix(
                    bug_report.fitxer_afectat.suffix + ".backup"
                )
                if backup_path.exists():
                    backup_path.unlink()

                return BugFix(
                    bug_report=bug_report,
                    fitxer_modificat=bug_report.fitxer_afectat,
                    diff=self._generate_diff(codi_original, codi_nou, str(bug_report.fitxer_afectat)),
                    codi_original=codi_original,
                    codi_nou=codi_nou,
                    explicacio=explicacio,
                    test_passa=True,
                    intents=intent,
                )
            else:
                self.log_warning(f"Test encara falla després de l'intent {intent}")
                last_error = output_test

                # Revertir si està configurat
                if revertir_si_falla:
                    self._revert_fix(bug_report.fitxer_afectat)

        # Tots els intents exhaurits
        self.log_warning(f"No s'ha pogut arreglar després de {self.max_intents} intents")

        return BugFix(
            bug_report=bug_report,
            fitxer_modificat=bug_report.fitxer_afectat,
            diff=self._generate_diff(codi_original, codi_nou, str(bug_report.fitxer_afectat)) if codi_original else "",
            codi_original=codi_original,
            codi_nou=codi_nou,
            explicacio=explicacio,
            test_passa=False,
            intents=self.max_intents,
            error_test=last_error,
        )


def main() -> None:
    """Exemple d'ús de l'agent."""
    import os
    os.environ["CLAUDECODE"] = "1"

    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax

    console = Console()

    # Crear un bug report de prova
    from agents.debug.models import BugReport

    report = BugReport(
        descripcio="La funció retorna None en lloc de llista buida",
        fitxer_afectat=Path("agents/base_agent.py"),
        funcio_afectada="extract_json_from_text",
        test_code="""
import pytest
from agents.base_agent import extract_json_from_text

def test_extract_json_returns_none_for_empty():
    \"\"\"Verifica que retorna None per text buit.\"\"\"
    result = extract_json_from_text("")
    assert result is None, "Hauria de retornar None per text buit"
""",
        passos_reproduccio=["Cridar extract_json_from_text amb string buit"],
        comportament_esperat="Retorna None",
        comportament_actual="Retorna None (correcte)",
    )

    console.print(Panel("BugFixerAgent - Demo", style="bold green"))

    agent = BugFixerAgent()
    fix = agent.fix(report, aplicar_canvis=False)  # Dry run

    console.print(f"\nTest passa: {fix.test_passa}")
    console.print(f"Intents: {fix.intents}")

    if fix.diff:
        console.print("\n[bold]Diff proposat:[/bold]")
        console.print(Syntax(fix.diff, "diff", theme="monokai"))


if __name__ == "__main__":
    main()
