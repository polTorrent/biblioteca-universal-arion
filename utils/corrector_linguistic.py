"""Corrector lingüístic integrat amb LanguageTool.

Proporciona correcció ortogràfica, gramatical i estilística per al català.
S'integra amb el pipeline de traducció per millorar la qualitat final.
"""

import re
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum

try:
    import language_tool_python
    LANGUAGETOOL_DISPONIBLE = True
except ImportError:
    LANGUAGETOOL_DISPONIBLE = False
    print("[CorrectorLinguistic] ⚠️ language-tool-python no instal·lat")


class CategoriaError(str, Enum):
    """Categories d'errors lingüístics."""
    ORTOGRAFIA = "ortografia"
    GRAMATICA = "gramatica"
    PUNTUACIO = "puntuacio"
    ESTIL = "estil"
    TIPOGRAFIA = "tipografia"
    BARBARISME = "barbarisme"
    ALTRES = "altres"


class ErrorLinguistic(BaseModel):
    """Un error detectat per LanguageTool."""
    categoria: CategoriaError
    missatge: str
    text_original: str
    suggeriments: list[str] = Field(default_factory=list)
    posicio_inici: int
    posicio_final: int
    regla_id: str = ""
    severitat: float = Field(ge=0, le=10, default=5.0)


class ResultatCorreccio(BaseModel):
    """Resultat complet de la correcció."""
    text_original: str
    text_corregit: str
    errors: list[ErrorLinguistic] = Field(default_factory=list)
    num_errors: int = 0
    num_correccions: int = 0
    puntuacio_normativa: float = Field(ge=0, le=10, default=10.0)

    # Estadístiques per categoria
    errors_ortografia: int = 0
    errors_gramatica: int = 0
    errors_puntuacio: int = 0
    errors_estil: int = 0
    errors_barbarisme: int = 0


class CorrectorLinguistic:
    """Corrector lingüístic basat en LanguageTool."""

    # Mapatge de categories de LanguageTool a les nostres
    MAPEIG_CATEGORIES = {
        "TYPOS": CategoriaError.ORTOGRAFIA,
        "SPELLING": CategoriaError.ORTOGRAFIA,
        "GRAMMAR": CategoriaError.GRAMATICA,
        "PUNCTUATION": CategoriaError.PUNTUACIO,
        "STYLE": CategoriaError.ESTIL,
        "TYPOGRAPHY": CategoriaError.TIPOGRAFIA,
        "CASING": CategoriaError.TIPOGRAFIA,
        "BARBARISM": CategoriaError.BARBARISME,
        "MISC": CategoriaError.ALTRES,
    }

    # Regles a ignorar (massa estrictes o falsos positius freqüents)
    REGLES_IGNORADES = {
        "WHITESPACE_RULE",
        "UPPERCASE_SENTENCE_START",
        "MORFOLOGIK_RULE_CA_ES",  # A vegades massa estricte amb noms propis
    }

    # Barbarismes específics a detectar (ampliable)
    BARBARISMES_EXTRA = {
        # Castellanismes freqüents
        "bueno": "bé, bo",
        "pues": "doncs, idò",
        "vale": "d'acord, entesos",
        "entonces": "llavors, aleshores",
        "luego": "després, més tard",
        "desde": "des de",
        "aunque": "encara que, tot i que",
        "sino": "sinó",
        "tampoco": "tampoc",
        "además": "a més",
        "incluso": "fins i tot",
        "mientras": "mentre",
        "todavía": "encara",
        "siempre": "sempre",
        "nunca": "mai",
        "ahora": "ara",
        "así": "així",
        "casi": "quasi, gairebé",
        "demasiado": "massa",
        "bastante": "bastant, força",
        "cualquier": "qualsevol",
        "alguien": "algú",
        "nadie": "ningú",
        "nada": "res",
        "algo": "alguna cosa",
        "mucho": "molt",
        "poco": "poc",
        "otro": "altre",
        "mismo": "mateix",
        "cada": "cada",
        "todo": "tot",
        "ambos": "ambdós",
        "varios": "diversos",
        "propio": "propi",
        "siguiente": "següent",
        "anterior": "anterior",
        "primero": "primer",
        "último": "últim, darrer",
        # Anglicismes
        "bàsicament": "fonamentalment, essencialment",
        "deliverar": "lliurar",
        "customitzar": "personalitzar",
        "targetitzar": "orientar, dirigir",
        "printear": "imprimir",
        "linkear": "enllaçar",
        "clickar": "fer clic, clicar",
        "resetear": "reiniciar",
        "updatejar": "actualitzar",
        "renderitzar": "renderitzar (acceptable) o generar",
    }

    _instance = None
    _tool = None

    def __new__(cls, llengua: str = "ca"):
        """Singleton per evitar múltiples connexions."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, llengua: str = "ca"):
        """
        Args:
            llengua: Codi de llengua ('ca', 'ca-ES', 'ca-ES-valencia')
        """
        if self._initialized:
            return

        self.llengua = llengua
        self._inicialitzar_tool()
        self._initialized = True

    def _inicialitzar_tool(self) -> None:
        """Inicialitza la connexió amb LanguageTool."""
        if not LANGUAGETOOL_DISPONIBLE:
            return

        if CorrectorLinguistic._tool is not None:
            return

        try:
            CorrectorLinguistic._tool = language_tool_python.LanguageTool(self.llengua)
            print(f"[CorrectorLinguistic] ✅ Inicialitzat per '{self.llengua}'")
        except Exception as e:
            print(f"[CorrectorLinguistic] ⚠️ Error inicialitzant: {e}")
            CorrectorLinguistic._tool = None

    @property
    def tool(self):
        return CorrectorLinguistic._tool

    def corregir(self, text: str, auto_corregir: bool = False) -> ResultatCorreccio:
        """Analitza i opcionalment corregeix un text.

        Args:
            text: Text a analitzar
            auto_corregir: Si True, aplica correccions automàtiques

        Returns:
            ResultatCorreccio amb errors trobats i text corregit
        """
        errors: list[ErrorLinguistic] = []
        text_corregit = text

        # 1. Detectar barbarismes extra (sempre, sense LanguageTool)
        errors.extend(self._detectar_barbarismes(text))

        # 2. Usar LanguageTool si disponible
        if self.tool:
            try:
                matches = self.tool.check(text)

                for match in matches:
                    # Compatibilitat amb noves versions (snake_case)
                    rule_id = getattr(match, 'rule_id', getattr(match, 'ruleId', ''))
                    error_length = getattr(match, 'error_length', getattr(match, 'errorLength', 0))

                    if rule_id in self.REGLES_IGNORADES:
                        continue

                    categoria = self._mapejar_categoria(match.category)
                    severitat = self._calcular_severitat(match, categoria)

                    errors.append(ErrorLinguistic(
                        categoria=categoria,
                        missatge=match.message,
                        text_original=text[match.offset:match.offset + error_length],
                        suggeriments=match.replacements[:5],
                        posicio_inici=match.offset,
                        posicio_final=match.offset + error_length,
                        regla_id=rule_id,
                        severitat=severitat,
                    ))

                if auto_corregir:
                    text_corregit = self.tool.correct(text)

            except Exception as e:
                print(f"[CorrectorLinguistic] Error en correcció: {e}")

        # 3. Calcular estadístiques
        stats = self._calcular_estadistiques(errors)

        # 4. Calcular puntuació normativa
        puntuacio = self._calcular_puntuacio(text, errors)

        return ResultatCorreccio(
            text_original=text,
            text_corregit=text_corregit if auto_corregir else text,
            errors=errors,
            num_errors=len(errors),
            num_correccions=len(errors) if auto_corregir else 0,
            puntuacio_normativa=puntuacio,
            **stats,
        )

    def _detectar_barbarismes(self, text: str) -> list[ErrorLinguistic]:
        """Detecta barbarismes no coberts per LanguageTool."""
        errors = []
        text_lower = text.lower()

        for barbarisme, alternatiu in self.BARBARISMES_EXTRA.items():
            pattern = rf'\b{re.escape(barbarisme)}\b'
            for match in re.finditer(pattern, text_lower):
                errors.append(ErrorLinguistic(
                    categoria=CategoriaError.BARBARISME,
                    missatge=f"Possible barbarisme: '{barbarisme}'",
                    text_original=text[match.start():match.end()],
                    suggeriments=[alternatiu],
                    posicio_inici=match.start(),
                    posicio_final=match.end(),
                    regla_id="ARION_BARBARISME",
                    severitat=6.0,
                ))

        return errors

    def _mapejar_categoria(self, categoria_lt: str) -> CategoriaError:
        """Mapeja categoria de LanguageTool a la nostra."""
        return self.MAPEIG_CATEGORIES.get(
            categoria_lt.upper(),
            CategoriaError.ALTRES
        )

    def _calcular_severitat(self, match, categoria: CategoriaError) -> float:
        """Calcula severitat d'un error."""
        severitats_base = {
            CategoriaError.ORTOGRAFIA: 7.0,
            CategoriaError.GRAMATICA: 6.0,
            CategoriaError.PUNTUACIO: 4.0,
            CategoriaError.ESTIL: 3.0,
            CategoriaError.TIPOGRAFIA: 3.0,
            CategoriaError.BARBARISME: 6.0,
            CategoriaError.ALTRES: 4.0,
        }
        return severitats_base.get(categoria, 5.0)

    def _calcular_estadistiques(self, errors: list[ErrorLinguistic]) -> dict:
        """Calcula estadístiques per categoria."""
        stats = {
            "errors_ortografia": 0,
            "errors_gramatica": 0,
            "errors_puntuacio": 0,
            "errors_estil": 0,
            "errors_barbarisme": 0,
        }

        for error in errors:
            key = f"errors_{error.categoria.value}"
            if key in stats:
                stats[key] += 1

        return stats

    def _calcular_puntuacio(self, text: str, errors: list[ErrorLinguistic]) -> float:
        """Calcula puntuació normativa (10 = perfecte)."""
        if not errors:
            return 10.0

        penalitzacio = sum(e.severitat * 0.1 for e in errors)
        paraules = len(text.split())
        factor = max(0.5, min(1.0, paraules / 200))

        puntuacio = 10.0 - (penalitzacio * factor)
        return max(0.0, min(10.0, round(puntuacio, 1)))

    def generar_informe(self, resultat: ResultatCorreccio) -> str:
        """Genera informe llegible dels errors."""
        linies = [
            "═" * 60,
            "        INFORME DE CORRECCIÓ LINGÜÍSTICA",
            "═" * 60,
            f"Puntuació normativa: {resultat.puntuacio_normativa}/10",
            f"Errors totals: {resultat.num_errors}",
            "",
            "Per categoria:",
            f"  • Ortografia: {resultat.errors_ortografia}",
            f"  • Gramàtica: {resultat.errors_gramatica}",
            f"  • Puntuació: {resultat.errors_puntuacio}",
            f"  • Estil: {resultat.errors_estil}",
            f"  • Barbarismes: {resultat.errors_barbarisme}",
            "",
        ]

        if resultat.errors:
            linies.append("DETALL D'ERRORS:")
            linies.append("-" * 40)

            for i, error in enumerate(resultat.errors[:20], 1):
                linies.append(f"{i}. [{error.categoria.value}] {error.missatge}")
                linies.append(f"   Text: \"{error.text_original}\"")
                if error.suggeriments:
                    linies.append(f"   Suggeriments: {', '.join(error.suggeriments[:3])}")
                linies.append("")

        linies.append("═" * 60)
        return "\n".join(linies)

    @classmethod
    def tancar(cls) -> None:
        """Tanca la connexió amb LanguageTool."""
        if cls._tool:
            try:
                cls._tool.close()
                cls._tool = None
                cls._instance = None
            except:
                pass


# Funcions helper
def corregir_text(text: str, auto_corregir: bool = False) -> ResultatCorreccio:
    """Funció helper per corregir text."""
    corrector = CorrectorLinguistic()
    return corrector.corregir(text, auto_corregir)


def obtenir_puntuacio_normativa(text: str) -> float:
    """Retorna només la puntuació normativa (0-10)."""
    resultat = corregir_text(text)
    return resultat.puntuacio_normativa


def es_languagetool_disponible() -> bool:
    """Comprova si LanguageTool està disponible."""
    return LANGUAGETOOL_DISPONIBLE
