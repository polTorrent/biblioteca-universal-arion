"""Agent per reproduir bugs i crear tests que fallen.

BugReproducerAgent analitza descripcions de bugs, localitza el codi afectat,
i genera tests pytest que demostren el problema.
"""

import re
import tempfile
from pathlib import Path
from typing import Any

from agents.base_agent import AgentConfig, BaseAgent
from agents.debug.models import BugReport


# System prompt per l'agent reproductor de bugs
BUG_REPRODUCER_SYSTEM_PROMPT = """Ets un enginyer QA expert en testing i debugging. La teva missió és:

1. ENTENDRE el bug descrit pel desenvolupador
2. LOCALITZAR el codi afectat basant-te en els fitxers proporcionats
3. ESCRIURE un test pytest MÍNIM que falli i demostri clarament el bug
4. DOCUMENTAR els passos exactes per reproduir-lo

Regles ESTRICTES:
- El test ha de ser ESPECÍFIC al bug descrit (no genèric)
- Ha de FALLAR amb el bug present i PASSAR quan es corregeixi
- Usa assertions clares amb missatges descriptius
- Escriu tots els comentaris en CATALÀ
- El test ha de ser autònom i executable
- Inclou els imports necessaris al test
- Usa noms descriptius: test_<funcionalitat>_<condicio>

Format de sortida OBLIGATORI (usa exactament aquestes etiquetes XML):

<fitxer_afectat>path/al/fitxer.py</fitxer_afectat>

<funcio>nom_de_la_funcio_o_metode</funcio>

<severitat>critica|alta|mitjana|baixa</severitat>

<test>
import pytest
# ... codi pytest complet i executable
def test_descripcio_del_bug():
    # Arranjament
    ...
    # Acció
    ...
    # Verificació
    assert resultat == esperat, "Missatge descriptiu del problema"
</test>

<passos>
1. Primer pas per reproduir
2. Segon pas
3. Tercer pas (resultat incorrecte)
</passos>

<esperat>Descripció clara del comportament correcte</esperat>

<actual>Descripció del comportament incorrecte actual</actual>

<context>Informació addicional rellevant per al diagnòstic (opcional)</context>
"""


class BugReproducerAgent(BaseAgent):
    """Agent especialitzat en reproduir bugs i crear tests.

    Analitza una descripció de bug (textual o d'una issue) juntament
    amb el codi font, i genera un test pytest que falla i demostra
    el problema de forma clara i reproducible.

    Example:
        >>> agent = BugReproducerAgent()
        >>> report = agent.reproduce(
        ...     descripcio="La funció retorna None en lloc de llista buida",
        ...     fitxers_context=["src/utils.py"]
        ... )
        >>> print(report.test_code)
    """

    agent_name = "BugReproducer"

    def __init__(
        self,
        config: AgentConfig | None = None,
        base_dir: Path | None = None,
    ) -> None:
        """Inicialitza l'agent.

        Args:
            config: Configuració de l'agent.
            base_dir: Directori base del projecte per llegir fitxers.
        """
        super().__init__(config=config)
        self.base_dir = base_dir or Path.cwd()

    @property
    def system_prompt(self) -> str:
        """Retorna el system prompt de l'agent."""
        return BUG_REPRODUCER_SYSTEM_PROMPT

    def _read_source_files(self, fitxers: list[str | Path]) -> str:
        """Llegeix els fitxers font i els formata per al prompt.

        Args:
            fitxers: Llista de camins als fitxers a llegir.

        Returns:
            String amb el contingut dels fitxers formatat.
        """
        continguts = []
        for fitxer in fitxers:
            path = self.base_dir / fitxer if not Path(fitxer).is_absolute() else Path(fitxer)
            if path.exists():
                try:
                    content = path.read_text(encoding="utf-8")
                    continguts.append(f"=== {fitxer} ===\n```python\n{content}\n```\n")
                except Exception as e:
                    self.log_warning(f"No s'ha pogut llegir {fitxer}: {e}")
            else:
                self.log_warning(f"Fitxer no trobat: {fitxer}")

        return "\n".join(continguts) if continguts else "[Cap fitxer llegit]"

    def _parse_response(self, response: str) -> dict[str, Any]:
        """Parseja la resposta de l'agent en un diccionari estructurat.

        Args:
            response: Resposta textual de l'agent.

        Returns:
            Diccionari amb els camps extrets.
        """
        result: dict[str, Any] = {}

        # Extreure cada camp amb regex
        patterns = {
            "fitxer_afectat": r"<fitxer_afectat>(.*?)</fitxer_afectat>",
            "funcio": r"<funcio>(.*?)</funcio>",
            "severitat": r"<severitat>(.*?)</severitat>",
            "test": r"<test>(.*?)</test>",
            "esperat": r"<esperat>(.*?)</esperat>",
            "actual": r"<actual>(.*?)</actual>",
            "context": r"<context>(.*?)</context>",
        }

        for camp, pattern in patterns.items():
            match = re.search(pattern, response, re.DOTALL)
            if match:
                result[camp] = match.group(1).strip()

        # Extreure passos com a llista
        passos_match = re.search(r"<passos>(.*?)</passos>", response, re.DOTALL)
        if passos_match:
            passos_text = passos_match.group(1).strip()
            # Parsejar línies numerades
            passos = []
            for line in passos_text.split("\n"):
                line = line.strip()
                # Treure número inicial si existeix
                line = re.sub(r"^\d+\.\s*", "", line)
                if line:
                    passos.append(line)
            result["passos"] = passos
        else:
            result["passos"] = []

        return result

    def _validate_test_syntax(self, test_code: str) -> bool:
        """Valida que el codi del test té sintaxi Python vàlida.

        Args:
            test_code: Codi del test a validar.

        Returns:
            True si la sintaxi és vàlida.
        """
        try:
            compile(test_code, "<test>", "exec")
            return True
        except SyntaxError as e:
            self.log_warning(f"Sintaxi invàlida al test: {e}")
            return False

    def _save_test(self, test_code: str, test_name: str) -> Path:
        """Guarda el test en un fitxer temporal.

        Args:
            test_code: Codi del test.
            test_name: Nom base per al fitxer.

        Returns:
            Camí al fitxer de test creat.
        """
        # Crear directori de tests temporals si no existeix
        tests_dir = self.base_dir / "tests" / "generated"
        tests_dir.mkdir(parents=True, exist_ok=True)

        # Netejar nom del fitxer
        safe_name = re.sub(r"[^a-z0-9_]", "_", test_name.lower())
        test_file = tests_dir / f"test_bug_{safe_name}.py"

        test_file.write_text(test_code, encoding="utf-8")
        return test_file

    def reproduce(
        self,
        descripcio: str,
        fitxers_context: list[str | Path] | None = None,
        guardar_test: bool = True,
    ) -> BugReport:
        """Reprodueix un bug i crea un test que el demostra.

        Args:
            descripcio: Descripció del bug a reproduir.
            fitxers_context: Fitxers de codi font per analitzar.
            guardar_test: Si s'ha de guardar el test en un fitxer.

        Returns:
            BugReport amb el test i la documentació.

        Raises:
            ValueError: Si no es pot generar un test vàlid.
        """
        fitxers_context = fitxers_context or []

        # Construir prompt amb context
        codi_font = self._read_source_files(fitxers_context)

        prompt = f"""## Descripció del Bug

{descripcio}

## Codi Font Relacionat

{codi_font}

## Tasca

Analitza el bug descrit i genera un test pytest que el demostri.
El test ha de FALLAR amb el codi actual.
"""

        # Cridar a l'agent
        self.log_info(f"Analitzant bug: {descripcio[:50]}...")
        response = self.process(prompt)

        # Parsejar resposta
        parsed = self._parse_response(response.content)

        # Validar camps obligatoris
        required = ["fitxer_afectat", "funcio", "test"]
        missing = [f for f in required if not parsed.get(f)]
        if missing:
            self.log_warning(f"Camps faltants a la resposta: {missing}")
            # Intentar extreure informació mínima
            if not parsed.get("fitxer_afectat"):
                parsed["fitxer_afectat"] = fitxers_context[0] if fitxers_context else "unknown.py"
            if not parsed.get("funcio"):
                parsed["funcio"] = "unknown"
            if not parsed.get("test"):
                raise ValueError("No s'ha pogut generar un test vàlid")

        # Validar sintaxi del test
        test_code = parsed["test"]
        if not self._validate_test_syntax(test_code):
            raise ValueError("El test generat té sintaxi invàlida")

        # Guardar test si cal
        test_file = None
        if guardar_test:
            # Generar nom basat en la funció
            test_name = parsed.get("funcio", "unknown")
            test_file = self._save_test(test_code, test_name)
            self.log_info(f"Test guardat a: {test_file}")

        # Determinar severitat
        severitat_raw = parsed.get("severitat", "mitjana").lower()
        if severitat_raw not in ("critica", "alta", "mitjana", "baixa"):
            severitat_raw = "mitjana"

        # Crear BugReport
        report = BugReport(
            descripcio=descripcio,
            fitxer_afectat=Path(parsed["fitxer_afectat"]),
            funcio_afectada=parsed["funcio"],
            test_code=test_code,
            test_file=test_file,
            passos_reproduccio=parsed.get("passos", []),
            comportament_esperat=parsed.get("esperat", "No especificat"),
            comportament_actual=parsed.get("actual", "No especificat"),
            severitat=severitat_raw,  # type: ignore
            context_adicional=parsed.get("context", ""),
        )

        self.log_info(f"Bug reproduït: {report.funcio_afectada} @ {report.fitxer_afectat}")
        return report


def main() -> None:
    """Exemple d'ús de l'agent."""
    import os
    os.environ["CLAUDECODE"] = "1"

    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax

    console = Console()

    agent = BugReproducerAgent()

    # Exemple de bug
    descripcio = """
    La funció extract_json_from_text a base_agent.py retorna None
    quan el JSON té comes finals (trailing commas), però hauria de
    poder parsejar-lo igualment o retornar un error més descriptiu.
    """

    console.print(Panel("BugReproducerAgent - Demo", style="bold blue"))

    try:
        report = agent.reproduce(
            descripcio=descripcio,
            fitxers_context=["agents/base_agent.py"],
            guardar_test=True,
        )

        console.print(f"\n[green]Bug reproduït correctament![/green]")
        console.print(f"Fitxer: {report.fitxer_afectat}")
        console.print(f"Funció: {report.funcio_afectada}")
        console.print(f"Severitat: {report.severitat}")
        console.print("\n[bold]Test generat:[/bold]")
        console.print(Syntax(report.test_code, "python", theme="monokai"))

        if report.test_file:
            console.print(f"\n[dim]Test guardat a: {report.test_file}[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise


if __name__ == "__main__":
    main()
