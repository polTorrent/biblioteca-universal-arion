"""Validador final per verificar que una obra està completa.

Comprova tots els requisits abans de publicar una obra a la web.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from core.memoria_contextual import MemoriaContextual

# Detecció de metadades filtrades (mateixa font de veritat que el pipeline).
# Import opcional: `core` també s'usa des d'scripts que no tenen
# `sistema/traduccio` al sys.path.
try:
    from agents.v2.sanititzacio import sembla_metadades, te_bloc_metadades
except ImportError:  # pragma: no cover
    sembla_metadades = None  # type: ignore[assignment]
    te_bloc_metadades = None  # type: ignore[assignment]

# Valors acceptats al camp d'estat (esquema vigent: `revisio.estat`).
# Els valors que indiquen feina en curs (`incomplet`, `pendent_*`, `en-procés`)
# NO són publicables.
ESTATS_PUBLICABLES = {
    "publicat",
    "revisat",
    "published",
    "reviewed",
    "validat",
    "consolidat",
    "completat",
    "corregit",
    "traduit",
    "traduït",
}


# =============================================================================
# MODELS PYDANTIC
# =============================================================================

class ItemValidacio(BaseModel):
    """Resultat d'una validació individual."""

    categoria: str  # "fitxer", "metadata", "contingut", "web", "coherencia", "notes", "introduccio"
    item: str
    descripcio: str
    obligatori: bool
    ok: bool
    error: str | None = None
    suggeriment: str | None = None


class ResultatValidacio(BaseModel):
    """Resultat complet de la validació."""

    obra_dir: str
    timestamp: str
    items: list[ItemValidacio] = Field(default_factory=list)
    errors_critics: int = 0
    warnings: int = 0
    puntuacio: float = 0.0
    pot_publicar: bool = False
    resum: str = ""


# =============================================================================
# CLASSE PRINCIPAL
# =============================================================================

class ValidadorFinal:
    """Validador final per verificar que una obra està completa.

    Comprova fitxers, metadata, contingut, coherència i generació web
    abans de permetre la publicació.

    Exemple d'ús:
        validador = ValidadorFinal(Path("obres/filosofia/plato/republica"))
        resultat = validador.validar()

        if resultat.pot_publicar:
            print("Obra llesta per publicar!")
        else:
            print(validador.generar_informe())
    """

    # Patrons problemàtics al contingut. Han de ser marques inequívoques: `XXX`
    # sol xoca amb els numerals romans dels encapçalaments («## XXX»), així que
    # només es considera marca si va entre claudàtors.
    PATRONS_PENDENTS = [
        (r"\[TODO\]", "Marca TODO pendent"),
        (r"\[PENDENT\]", "Marca PENDENT"),
        (r"\?\?\?", "Interrogants de dubte"),
        (r"\[XXX\]", "Marca XXX pendent"),
        (r"FIXME", "Marca FIXME"),
    ]

    def __init__(self, obra_dir: Path) -> None:
        """Inicialitza el validador.

        Args:
            obra_dir: Directori de l'obra a validar.
        """
        self.obra_dir = Path(obra_dir)
        self._metadata: dict | None = None
        self._traduccio: str | None = None
        self._original: str | None = None
        self._glossari: list[dict] | None = None
        self._introduccio: str | None = None
        self._notes: str | None = None

        print(f"[ValidadorFinal] Inicialitzat per: {self.obra_dir}")

    # =========================================================================
    # CÀRREGA DE FITXERS
    # =========================================================================

    def _carregar_metadata(self) -> dict | None:
        """Carrega i parseja metadata.yml."""
        if self._metadata is not None:
            return self._metadata

        fitxer = self.obra_dir / "metadata.yml"
        if not fitxer.exists():
            return None

        try:
            contingut = fitxer.read_text(encoding="utf-8")
            self._metadata = yaml.safe_load(contingut) or {}
            return self._metadata
        except Exception as e:
            print(f"[ValidadorFinal] Error llegint metadata: {e}")
            return None

    # =========================================================================
    # LECTURA DE METADADES (esquema vigent + esquema antic)
    # =========================================================================

    def _camp_metadata(self, *claus: str) -> str:
        """Llegeix un camp de metadata.yml tolerant amb els dos esquemes.

        El catàleg fa servir l'esquema niuat en català (`obra.titol`,
        `obra.autor`, `obra.llengua_original`…, i `revisio.estat`,
        `revisio.qualitat`, `revisio.data_revisio`); els primers fitxers
        portaven els camps plans anglesos (`title`, `author`…). Es proven tots
        dos, en l'ordre indicat.

        Args:
            *claus: Noms de camp per ordre de prioritat.

        Returns:
            El valor com a text, o cadena buida si no hi és.
        """
        metadata = self._carregar_metadata() or {}
        obres = metadata.get("obra") if isinstance(metadata.get("obra"), dict) else {}
        revisio = metadata.get("revisio") if isinstance(metadata.get("revisio"), dict) else {}
        fonts = (obres, revisio, metadata)
        for clau in claus:
            for font in fonts:
                valor = font.get(clau) if isinstance(font, dict) else None
                if valor not in (None, "", [], {}):
                    return str(valor)
        return ""

    def _qualitat_metadata(self) -> float | None:
        """Retorna la puntuació de qualitat declarada (metadata o `.validated`)."""
        text = self._camp_metadata("qualitat", "quality_score", "puntuacio", "puntuació")
        if text:
            coincidencia = re.search(r"\d+(?:[.,]\d+)?", text)
            if coincidencia:
                try:
                    return float(coincidencia.group(0).replace(",", "."))
                except ValueError:
                    pass

        # Marcador `.validated` (format: «Puntuació: 7.5/10»)
        fitxer = self.obra_dir / ".validated"
        if fitxer.exists():
            try:
                contingut = fitxer.read_text(encoding="utf-8")
            except Exception:
                return None
            coincidencia = re.search(r"[Pp]untuaci[oó]\s*:?\s*(\d+(?:[.,]\d+)?)", contingut)
            if coincidencia:
                try:
                    return float(coincidencia.group(1).replace(",", "."))
                except ValueError:
                    return None
        return None

    def _te_marcador_validat(self) -> bool:
        """True si l'obra té el marcador `.validated`."""
        return (self.obra_dir / ".validated").exists()

    def _carregar_traduccio(self) -> str | None:
        """Carrega traduccio.md."""
        if self._traduccio is not None:
            return self._traduccio

        fitxer = self.obra_dir / "traduccio.md"
        if not fitxer.exists():
            return None

        try:
            self._traduccio = fitxer.read_text(encoding="utf-8")
            return self._traduccio
        except Exception as e:
            print(f"[ValidadorFinal] Error llegint traducció: {e}")
            return None

    def _carregar_original(self) -> str | None:
        """Carrega original.md."""
        if self._original is not None:
            return self._original

        fitxer = self.obra_dir / "original.md"
        if not fitxer.exists():
            return None

        try:
            self._original = fitxer.read_text(encoding="utf-8")
            return self._original
        except Exception as e:
            print(f"[ValidadorFinal] Error llegint original: {e}")
            return None

    def _carregar_glossari(self) -> list[dict] | None:
        """Carrega i parseja glossari.yml."""
        if self._glossari is not None:
            return self._glossari

        fitxer = self.obra_dir / "glossari.yml"
        if not fitxer.exists():
            return None

        try:
            contingut = fitxer.read_text(encoding="utf-8")
            data = yaml.safe_load(contingut)

            # Pot ser una llista directa o un dict amb clau "glossari"
            if isinstance(data, list):
                self._glossari = data
            elif isinstance(data, dict):
                self._glossari = data.get("glossari", data.get("termes", []))
            else:
                self._glossari = []

            return self._glossari
        except Exception as e:
            print(f"[ValidadorFinal] Error llegint glossari: {e}")
            return None

    def _carregar_introduccio(self) -> str | None:
        """Carrega introduccio.md."""
        if self._introduccio is not None:
            return self._introduccio

        fitxer = self.obra_dir / "introduccio.md"
        if not fitxer.exists():
            return None

        try:
            self._introduccio = fitxer.read_text(encoding="utf-8")
            return self._introduccio
        except Exception as e:
            print(f"[ValidadorFinal] Error llegint introducció: {e}")
            return None

    def _carregar_notes(self) -> str | None:
        """Carrega notes.md."""
        if self._notes is not None:
            return self._notes

        fitxer = self.obra_dir / "notes.md"
        if not fitxer.exists():
            return None

        try:
            self._notes = fitxer.read_text(encoding="utf-8")
            return self._notes
        except Exception as e:
            print(f"[ValidadorFinal] Error llegint notes: {e}")
            return None

    def _comptar_paraules(self, text: str) -> int:
        """Compta paraules d'un text."""
        if not text:
            return 0
        # Eliminar markdown i comptar
        text_net = re.sub(r"[#*_`\[\]()>]", " ", text)
        paraules = text_net.split()
        return len(paraules)

    # =========================================================================
    # VALIDACIONS
    # =========================================================================

    def validar_integritat(self) -> list[ItemValidacio]:
        """Verifica que la traducció no conté al·lucinacions.

        PRIORITAT MÀXIMA — s'executa ABANS de tots els altres checks.
        Compara estructura original vs traducció per detectar contingut inventat.
        """
        items: list[ItemValidacio] = []

        original = self._carregar_original()
        traduccio = self._carregar_traduccio()

        if not original or not traduccio:
            return items

        # --- Check 1: Ratio de longitud ---
        ratio = len(traduccio) / len(original) if original else 0

        items.append(ItemValidacio(
            categoria="integritat",
            item="ratio_longitud",
            descripcio="Proporció original/traducció dins rang normal (0.4-2.5x)",
            obligatori=True,
            ok=0.15 <= ratio <= 5.0,
            error=(f"Ratio sospitós: {ratio:.2f}x "
                   f"(orig={len(original)}, trad={len(traduccio)})")
                   if not (0.15 <= ratio <= 5.0) else None,
            suggeriment="Possible al·lucinació o omissió massiva. Revisar manualment.",
        ))

        # --- Check 2: Recompte d'unitats numerades ---
        patrons = [
            r'(?:^|\n)### (\d+)',
            r'(?:^|\n)\*\*(\d+)\.\*\*',
            r'(?:^|\n)(\d+)\.\s',
            r'(?:^|\n)§\s*(\d+)',
        ]

        nums_orig: set[str] = set()
        nums_trad: set[str] = set()
        for patro in patrons:
            nums_orig.update(re.findall(patro, original))
            nums_trad.update(re.findall(patro, traduccio))

        if nums_orig:  # Només si el text té numeració
            inventats = nums_trad - nums_orig
            falten = nums_orig - nums_trad

            error_msg = None
            if inventats or falten:
                parts = []
                if inventats:
                    parts.append(f"Unitats inventades: {sorted(inventats)[:10]}")
                if falten:
                    parts.append(f"Unitats omeses: {sorted(falten)[:10]}")
                error_msg = ". ".join(parts)

            # Només és crític si l'original té una numeració consolidada: amb
            # poques unitats al costat original, les diferències solen ser
            # maneres distintes de numerar (encapçalaments afegits pel pipeline).
            items.append(ItemValidacio(
                categoria="integritat",
                item="recompte_unitats",
                descripcio="Totes les unitats de l'original existeixen a la traducció",
                obligatori=len(nums_orig) >= 5 and bool(inventats or falten),
                ok=len(inventats) == 0 and len(falten) == 0,
                error=error_msg,
                suggeriment="🚨 POSSIBLE AL·LUCINACIÓ. Revisar traducció manualment."
                if len(nums_orig) >= 5 else "Revisar si la numeració de la traducció és intencionada.",
            ))

        # --- Check 3: Paràgrafs (per textos sense numeració) ---
        if not nums_orig:
            par_orig = self._comptar_paragrafs_contingut(original)
            par_trad = self._comptar_paragrafs_contingut(traduccio)

            diferencia = abs(par_orig - par_trad)
            llindar = max(5, int(par_orig * 0.40))

            # AVÍS, no porta de publicació: en vers (una línia per vers a
            # l'original) i en originals CJK el recompte de paràgrafs no és
            # comparable. Per a omissions massives ja hi ha `ratio_longitud`.
            items.append(ItemValidacio(
                categoria="integritat",
                item="recompte_paragrafs",
                descripcio=f"Nombre de paràgrafs similar (orig={par_orig}, trad={par_trad})",
                obligatori=False,
                ok=diferencia <= llindar,
                error=f"Diferència de {diferencia} paràgrafs (orig={par_orig}, trad={par_trad})",
                suggeriment="Revisar si falten paràgrafs (en vers i en textos CJK el recompte sol desquadrar)",
            ))

        return items

    def _comptar_paragrafs_contingut(self, text: str) -> int:
        """Compta paràgrafs de contingut, sense encapçalaments ni capçalera.

        Els encapçalaments markdown (`## Capítol XX`), el bloc de capçalera que
        afegeix el pipeline (títol, autor, «Traduït del…», separador) i les notes
        numerades no són paràgrafs de text i desquadraven el recompte.
        """
        net = re.sub(r"^#{1,6}\s.*$", "", text, flags=re.MULTILINE)
        net = re.sub(r"^\s*[-*]{3,}\s*$", "", net, flags=re.MULTILINE)
        net = re.sub(r"^\s*\*[^*]{0,120}\*\s*$", "", net, flags=re.MULTILINE)
        net = re.sub(r"^\s*Traduït del .*$", "", net, flags=re.MULTILINE | re.IGNORECASE)
        return len([p for p in net.split("\n\n") if len(p.strip()) > 30])

    def validar_fitxers(self) -> list[ItemValidacio]:
        """Valida l'existència dels fitxers obligatoris."""
        items: list[ItemValidacio] = []

        # metadata.yml
        fitxer = self.obra_dir / "metadata.yml"
        items.append(ItemValidacio(
            categoria="fitxer",
            item="metadata.yml",
            descripcio="Fitxer de metadades de l'obra",
            obligatori=True,
            ok=fitxer.exists(),
            error=None if fitxer.exists() else "Fitxer metadata.yml no trobat",
            suggeriment="Crear metadata.yml amb el bloc 'obra:' (titol, autor, llengua_original) i 'revisio:'",
        ))

        # original.md
        fitxer = self.obra_dir / "original.md"
        original = self._carregar_original()
        te_contingut = bool(original and len(original.strip()) > 100)
        items.append(ItemValidacio(
            categoria="fitxer",
            item="original.md",
            descripcio="Text original de l'obra",
            obligatori=True,
            ok=te_contingut,
            error=None if te_contingut else "original.md no existeix o està buit",
            suggeriment="Afegir el text original complet a original.md",
        ))

        # traduccio.md
        fitxer = self.obra_dir / "traduccio.md"
        traduccio = self._carregar_traduccio()
        te_contingut = bool(traduccio and len(traduccio.strip()) > 100)
        items.append(ItemValidacio(
            categoria="fitxer",
            item="traduccio.md",
            descripcio="Traducció al català",
            obligatori=True,
            ok=te_contingut,
            error=None if te_contingut else "traduccio.md no existeix o està buit",
            suggeriment="Completar la traducció a traduccio.md",
        ))

        # glossari.yml
        fitxer = self.obra_dir / "glossari.yml"
        glossari = self._carregar_glossari()
        es_valid = glossari is not None
        items.append(ItemValidacio(
            categoria="fitxer",
            item="glossari.yml",
            descripcio="Glossari de termes",
            obligatori=True,
            ok=es_valid,
            error=None if es_valid else "glossari.yml no existeix o no és YAML vàlid",
            suggeriment="Crear glossari.yml amb format YAML vàlid",
        ))

        # portada.png o portada.jpg (OBLIGATORI)
        portada_png = self.obra_dir / "portada.png"
        portada_jpg = self.obra_dir / "portada.jpg"
        te_portada = portada_png.exists() or portada_jpg.exists()
        items.append(ItemValidacio(
            categoria="fitxer",
            item="portada.png/jpg",
            descripcio="Imatge de portada de l'obra",
            obligatori=True,
            ok=te_portada,
            error=None if te_portada else "No hi ha portada.png ni portada.jpg",
            suggeriment="Afegir portada.png (preferit) o portada.jpg al directori de l'obra",
        ))

        # introduccio.md (recomanat, NO obligatori: només 14 de 97 obres en tenen
        # i el catàleg publica notes.md com a estudi crític)
        intro = self._carregar_introduccio()
        paraules_intro = self._comptar_paraules(intro) if intro else 0
        te_intro = paraules_intro >= 200
        items.append(ItemValidacio(
            categoria="fitxer",
            item="introduccio.md",
            descripcio="Estudi introductori (mínim 200 paraules)",
            obligatori=False,
            ok=te_intro,
            error=None if te_intro else f"introduccio.md no existeix o és massa breu ({paraules_intro} paraules)",
            suggeriment="Crear introduccio.md amb context sobre l'autor, l'obra i la traducció (mínim 200 paraules)",
        ))

        return items

    def validar_metadata(self) -> list[ItemValidacio]:
        """Valida els camps de metadata.yml."""
        items: list[ItemValidacio] = []
        metadata = self._carregar_metadata()

        if not metadata:
            items.append(ItemValidacio(
                categoria="metadata",
                item="metadata.yml",
                descripcio="Fitxer de metadades",
                obligatori=True,
                ok=False,
                error="No s'ha pogut carregar metadata.yml",
                suggeriment="Verificar que metadata.yml existeix i és YAML vàlid",
            ))
            return items

        # title (esquema vigent: obra.titol)
        title = self._camp_metadata("titol", "title")
        items.append(ItemValidacio(
            categoria="metadata",
            item="title",
            descripcio="Títol de l'obra",
            obligatori=True,
            ok=bool(title),
            error=None if title else "Camp 'obra.titol' (o 'title') buit o absent",
            suggeriment="Afegir 'titol: Títol de l'Obra' dins 'obra:' a metadata.yml",
        ))

        # author (esquema vigent: obra.autor)
        author = self._camp_metadata("autor", "author")
        items.append(ItemValidacio(
            categoria="metadata",
            item="author",
            descripcio="Autor de l'obra",
            obligatori=True,
            ok=bool(author),
            error=None if author else "Camp 'obra.autor' (o 'author') buit o absent",
            suggeriment="Afegir 'autor: Nom de l'Autor' dins 'obra:' a metadata.yml",
        ))

        # source_language (esquema vigent: obra.llengua_original)
        lang = self._camp_metadata("llengua_original", "source_language", "llengua")
        items.append(ItemValidacio(
            categoria="metadata",
            item="source_language",
            descripcio="Llengua original",
            obligatori=True,
            ok=bool(lang),
            error=None if lang else "Camp 'obra.llengua_original' (o 'source_language') buit o absent",
            suggeriment="Afegir 'llengua_original: grec/llatí/japonès/etc.' dins 'obra:' a metadata.yml",
        ))

        # status (esquema vigent: revisio.estat, o el marcador .validated)
        status = self._camp_metadata("estat", "status").strip().lower()
        te_validated = self._te_marcador_validat()
        status_valid = status in ESTATS_PUBLICABLES or te_validated
        items.append(ItemValidacio(
            categoria="metadata",
            item="status",
            descripcio="Estat de la traducció (revisat/publicat o marcador .validated)",
            obligatori=True,
            ok=status_valid,
            error=None if status_valid else (
                f"Estat '{status or '(buit)'}' no és publicable i no hi ha marcador .validated"
            ),
            suggeriment="Posar 'estat: revisat' dins 'revisio:' a metadata.yml o crear el fitxer .validated",
        ))

        # quality_score (esquema vigent: revisio.qualitat o .validated)
        quality = self._qualitat_metadata()
        quality_ok = quality is not None and quality >= 7.0
        items.append(ItemValidacio(
            categoria="metadata",
            item="quality_score",
            descripcio="Puntuació de qualitat (mínim 7.0)",
            obligatori=True,
            ok=quality_ok,
            error=None if quality_ok else (
                "No hi ha puntuació de qualitat a metadata.yml (revisio.qualitat) "
                "ni al marcador .validated"
                if quality is None
                else f"qualitat ({quality}) és inferior a 7.0"
            ),
            suggeriment="Posar 'qualitat: X.X' dins 'revisio:' a metadata.yml o validar l'obra (mínim 7.0)",
        ))

        # date (esquema vigent: revisio.data_revisio / obra.any_traduccio)
        date = self._camp_metadata("data_revisio", "date", "any_traduccio", "any")
        items.append(ItemValidacio(
            categoria="metadata",
            item="date",
            descripcio="Data de la traducció o de la revisió",
            obligatori=True,
            ok=bool(date),
            error=None if date else "Camp 'revisio.data_revisio' (o 'date'/'obra.any_traduccio') buit o absent",
            suggeriment="Afegir 'data_revisio: YYYY-MM-DD' dins 'revisio:' a metadata.yml",
        ))

        return items

    def validar_contingut_traduccio(self) -> list[ItemValidacio]:
        """Valida el contingut de traduccio.md."""
        items: list[ItemValidacio] = []
        traduccio = self._carregar_traduccio()

        if not traduccio:
            items.append(ItemValidacio(
                categoria="contingut",
                item="traduccio.md",
                descripcio="Contingut de la traducció",
                obligatori=True,
                ok=False,
                error="No s'ha pogut carregar traduccio.md",
                suggeriment="Verificar que traduccio.md existeix",
            ))
            return items

        # Comprovar patrons pendents
        for patro, desc in self.PATRONS_PENDENTS:
            matches = re.findall(patro, traduccio, re.IGNORECASE)
            items.append(ItemValidacio(
                categoria="contingut",
                item=f"sense_{patro}",
                descripcio=f"No conté '{desc}'",
                obligatori=True,
                ok=len(matches) == 0,
                error=f"Trobats {len(matches)} casos de '{desc}'" if matches else None,
                suggeriment=f"Eliminar o resoldre totes les marques '{desc}'",
            ))

        # No conté metadades internes del refinador (JSON filtrat) ni marques
        # d'error: això sí que bloqueja la publicació.
        te_metadades = bool(
            (te_bloc_metadades and te_bloc_metadades(traduccio))
            or (sembla_metadades and sembla_metadades(traduccio))
        )
        te_errors = "[ERROR:" in traduccio
        items.append(ItemValidacio(
            categoria="contingut",
            item="sense_metadades_filtrades",
            descripcio="No conté metadades internes del refinador ni marques d'error",
            obligatori=True,
            ok=not (te_metadades or te_errors),
            error=(
                "Hi ha un bloc de metadades del refinador (JSON filtrat) dins la traducció"
                if te_metadades
                else ("Hi ha marques [ERROR:] d'execucions fallides" if te_errors else None)
            ),
            suggeriment="Netejar amb sistema/scripts/neteja_blocs_metadades.py i retraduir els fragments afectats",
        ))

        # Blocs de codi: avís (els índexs de ```català són legítims; les
        # metadades filtrades ja es detecten a l'item anterior).
        blocs_codi = re.findall(r"```", traduccio)
        items.append(ItemValidacio(
            categoria="contingut",
            item="sense_blocs_codi",
            descripcio="No conté blocs de codi sense processar",
            obligatori=False,
            ok=len(blocs_codi) == 0,
            error=f"Trobats {len(blocs_codi)//2} blocs de codi" if blocs_codi else None,
            suggeriment="Revisar si els blocs de codi (```) són contingut legítim (índexs) o restes del model",
        ))

        # Mínim de paraules
        paraules = self._comptar_paraules(traduccio)
        items.append(ItemValidacio(
            categoria="contingut",
            item="minim_paraules",
            descripcio="Mínim 100 paraules",
            obligatori=True,
            ok=paraules >= 100,
            error=f"Només {paraules} paraules" if paraules < 100 else None,
            suggeriment="La traducció ha de tenir almenys 100 paraules",
        ))

        # Línies buides consecutives
        linies_buides = re.findall(r"\n{5,}", traduccio)
        items.append(ItemValidacio(
            categoria="contingut",
            item="linies_buides",
            descripcio="No té línies buides excessives (>3 consecutives)",
            obligatori=False,
            ok=len(linies_buides) == 0,
            error=f"Trobats {len(linies_buides)} blocs de línies buides excessives" if linies_buides else None,
            suggeriment="Reduir línies buides consecutives a màxim 2",
        ))

        return items

    def validar_introduccio(self) -> list[ItemValidacio]:
        """Valida l'estudi introductori (recomanat, no obligatori)."""
        items: list[ItemValidacio] = []
        intro = self._carregar_introduccio()

        if not intro:
            items.append(ItemValidacio(
                categoria="introduccio",
                item="introduccio.md",
                descripcio="Existència de l'estudi introductori",
                obligatori=False,
                ok=False,
                error="No existeix introduccio.md",
                suggeriment="Crear introduccio.md amb estudi introductori",
            ))
            return items

        # Mínim paraules
        paraules = self._comptar_paraules(intro)
        items.append(ItemValidacio(
            categoria="introduccio",
            item="minim_paraules",
            descripcio="Mínim 200 paraules",
            obligatori=False,
            ok=paraules >= 200,
            error=f"Només {paraules} paraules (mínim 200)" if paraules < 200 else None,
            suggeriment="Ampliar l'estudi introductori a mínim 200 paraules",
        ))

        # Seccions esperades (opcionals però recomanades)
        intro_lower = intro.lower()
        seccions_esperades = [
            ("context", ["context", "marc", "època", "històric"]),
            ("autor", ["autor", "vida", "biografia"]),
            ("obra", ["obra", "text", "contingut", "argument"]),
        ]

        for nom, paraules_clau in seccions_esperades:
            te_seccio = any(p in intro_lower for p in paraules_clau)
            items.append(ItemValidacio(
                categoria="introduccio",
                item=f"seccio_{nom}",
                descripcio=f"Secció sobre {nom}",
                obligatori=False,
                ok=te_seccio,
                error=f"No s'ha trobat secció sobre '{nom}'" if not te_seccio else None,
                suggeriment=f"Afegir informació sobre {nom} a la introducció",
            ))

        return items

    def validar_notes_traductor(self) -> list[ItemValidacio]:
        """Valida les notes del traductor per edicions crítiques."""
        items: list[ItemValidacio] = []
        metadata = self._carregar_metadata() or {}
        traduccio = self._carregar_traduccio() or ""

        # Determinar si és edició crítica
        es_critica = (
            metadata.get("edicio_critica", False) or
            metadata.get("tipus_edicio", "").lower() == "critica" or
            metadata.get("tipus_edicio", "").lower() == "crítica"
        )

        if not es_critica:
            items.append(ItemValidacio(
                categoria="notes",
                item="edicio_critica",
                descripcio="Verificació d'edició crítica",
                obligatori=False,
                ok=True,
                error=None,
                suggeriment=None,
            ))
            return items

        # Per edicions crítiques, cal notes
        notes = self._carregar_notes()
        notes_integrades = re.findall(r"\[\^?\d+\]", traduccio)

        te_notes = notes or len(notes_integrades) > 0
        items.append(ItemValidacio(
            categoria="notes",
            item="existencia_notes",
            descripcio="Existència de notes (edició crítica)",
            obligatori=True,
            ok=te_notes,
            error="Edició crítica sense notes" if not te_notes else None,
            suggeriment="Afegir notes.md o notes integrades [^1] a traduccio.md",
        ))

        if not te_notes:
            return items

        # Verificar format de notes
        text_notes = notes or traduccio
        tipus_notes = ["[T]", "[H]", "[F]", "[L]", "[C]", "[R]", "[B]"]
        te_tipus = any(t in text_notes for t in tipus_notes)
        items.append(ItemValidacio(
            categoria="notes",
            item="format_notes",
            descripcio="Notes amb tipus [T], [H], [F], [L], [C], [R]",
            obligatori=False,
            ok=te_tipus,
            error="Notes sense tipus definit" if not te_tipus else None,
            suggeriment="Afegir tipus a les notes: [T]raducció, [H]istòrica, [F]ilosòfica, [L]iterària, [C]ultural, [R]eferència",
        ))

        # Mínim de notes per 1000 paraules
        paraules_trad = self._comptar_paraules(traduccio)
        num_notes = len(re.findall(r"\[\^?\d+\]", text_notes))

        if notes:
            # Comptar notes al fitxer notes.md
            num_notes = len(re.findall(r"##\s*\[\d+\]", notes))

        notes_esperades = max(5, int(paraules_trad / 1000) * 5)
        items.append(ItemValidacio(
            categoria="notes",
            item="densitat_notes",
            descripcio=f"Mínim {notes_esperades} notes per {paraules_trad} paraules",
            obligatori=False,
            ok=num_notes >= notes_esperades,
            error=f"Només {num_notes} notes (esperades {notes_esperades})" if num_notes < notes_esperades else None,
            suggeriment="Afegir més notes explicatives per a una edició crítica completa",
        ))

        # Verificar referències
        refs_traduccio = set(re.findall(r"\[\^?(\d+)\]", traduccio))
        if notes:
            refs_notes = set(re.findall(r"##\s*\[(\d+)\]", notes))
            refs_sense_nota = refs_traduccio - refs_notes
            items.append(ItemValidacio(
                categoria="notes",
                item="refs_completes",
                descripcio="Totes les referències tenen nota corresponent",
                obligatori=True,
                ok=len(refs_sense_nota) == 0,
                error=f"Referències sense nota: {refs_sense_nota}" if refs_sense_nota else None,
                suggeriment="Afegir les notes que falten a notes.md",
            ))

        return items

    def validar_glossari(self) -> list[ItemValidacio]:
        """Valida el glossari."""
        items: list[ItemValidacio] = []
        glossari = self._carregar_glossari()

        if glossari is None:
            items.append(ItemValidacio(
                categoria="glossari",
                item="glossari.yml",
                descripcio="Glossari vàlid",
                obligatori=True,
                ok=False,
                error="No s'ha pogut carregar glossari.yml",
                suggeriment="Verificar que glossari.yml existeix i és YAML vàlid",
            ))
            return items

        # Mínim de termes
        items.append(ItemValidacio(
            categoria="glossari",
            item="minim_termes",
            descripcio="Mínim 3 termes",
            obligatori=True,
            ok=len(glossari) >= 3,
            error=f"Només {len(glossari)} termes" if len(glossari) < 3 else None,
            suggeriment="Afegir almenys 3 termes al glossari",
        ))

        # Verificar estructura de cada terme. El glossari del catàleg fa servir
        # claus de llengua variables (`italia`, `grec`, `llati`, `angles`…), a més
        # de `original`/`terme`; per tant es considera que un terme té l'original
        # si té alguna clau de text que no sigui la traducció ni camps auxiliars.
        termes_incomplets = []
        claus_auxiliars = {
            "traduccio",
            "traducció",
            "catala",
            "català",
            "definicio",
            "definició",
            "significat",
            "significado",
            "explicacio",
            "explicació",
            "gloss",
            "translation",
            "transliteracio",
            "transliteració",
            "nota",
            "notes",
            "comentari",
            "comentaris",
            "categoria",
            "tipus",
            "font",
            "referencia",
        }
        for i, terme in enumerate(glossari):
            if not isinstance(terme, dict):
                termes_incomplets.append(f"#{i+1} (no és dict)")
                continue

            te_traduccio = any(
                k in terme
                for k in [
                    "traduccio",
                    "traducció",
                    "catala",
                    "català",
                    "definicio",
                    "definició",
                    "significat",
                    "significado",
                    "explicacio",
                    "explicació",
                    "gloss",
                    "translation",
                ]
            )
            te_original = any(
                clau not in claus_auxiliars and isinstance(valor, str) and valor.strip()
                for clau, valor in terme.items()
            )

            if not te_original or not te_traduccio:
                termes_incomplets.append(f"#{i+1}")

        items.append(ItemValidacio(
            categoria="glossari",
            item="estructura_termes",
            descripcio="Cada terme té 'original' i 'traduccio'",
            obligatori=True,
            ok=len(termes_incomplets) == 0,
            error=f"Termes incomplets: {', '.join(termes_incomplets)}" if termes_incomplets else None,
            suggeriment="Afegir camps 'original' i 'traduccio' a cada terme",
        ))

        # Verificar que els termes apareixen a la traducció
        traduccio = self._carregar_traduccio() or ""
        traduccio_lower = traduccio.lower()
        termes_no_usats = []

        for terme in glossari:
            if not isinstance(terme, dict):
                continue
            original = terme.get("original", terme.get("terme", terme.get("grec", "")))
            if original and original.lower() not in traduccio_lower:
                termes_no_usats.append(original)

        items.append(ItemValidacio(
            categoria="glossari",
            item="termes_usats",
            descripcio="Els termes del glossari apareixen a la traducció",
            obligatori=False,
            ok=len(termes_no_usats) == 0,
            error=f"Termes no trobats: {', '.join(termes_no_usats[:5])}" if termes_no_usats else None,
            suggeriment="Revisar si els termes del glossari són correctes",
        ))

        return items

    def validar_coherencia(self, memoria: "MemoriaContextual | None" = None) -> list[ItemValidacio]:
        """Valida la coherència del contingut."""
        items: list[ItemValidacio] = []
        traduccio = self._carregar_traduccio() or ""

        # Termes sense traduir (entre cometes o cursiva repetits)
        # Buscar patrons com "terme" o *terme* que es repeteixen
        termes_cursiva = re.findall(r"\*([^*]+)\*", traduccio)
        termes_cometes = re.findall(r'"([^"]+)"', traduccio)

        # Comptar repeticions
        from collections import Counter
        repetits_cursiva = [t for t, c in Counter(termes_cursiva).items() if c >= 3 and len(t) > 3]
        repetits_cometes = [t for t, c in Counter(termes_cometes).items() if c >= 3 and len(t) > 3]

        termes_sospitosos = repetits_cursiva + repetits_cometes
        items.append(ItemValidacio(
            categoria="coherencia",
            item="termes_estrangers",
            descripcio="No hi ha termes sense traduir repetits",
            obligatori=False,
            ok=len(termes_sospitosos) == 0,
            error=f"Possibles termes sense traduir: {', '.join(termes_sospitosos[:5])}" if termes_sospitosos else None,
            suggeriment="Revisar si aquests termes s'haurien de traduir o afegir al glossari",
        ))

        # Si tenim memòria contextual, verificar consistència
        if memoria:
            traduccions = memoria.obtenir_totes_traduccions()
            inconsistencies = []

            for trad in traduccions:
                # Verificar que el terme traduït apareix a la traducció
                if trad.traduccio.lower() not in traduccio.lower():
                    inconsistencies.append(f"{trad.original}→{trad.traduccio}")

            items.append(ItemValidacio(
                categoria="coherencia",
                item="memoria_consistent",
                descripcio="Traduccions de la memòria contextual presents",
                obligatori=False,
                ok=len(inconsistencies) == 0,
                error=f"Traduccions no trobades: {', '.join(inconsistencies[:5])}" if inconsistencies else None,
                suggeriment="Verificar que les traduccions registrades s'han aplicat",
            ))

        return items

    def validar_web(self) -> list[ItemValidacio]:
        """Valida la generació web."""
        items: list[ItemValidacio] = []

        # Directori docs/ (a l'arrel del repositori: <arrel>/obres/<cat>/<autor>/<obra>)
        try:
            docs_dir = self.obra_dir.resolve().parents[3] / "docs"
        except IndexError:  # estructura inesperada (p. ex. una prova temporal)
            docs_dir = self.obra_dir / "docs"
        if not docs_dir.exists():
            items.append(ItemValidacio(
                categoria="web",
                item="docs_dir",
                descripcio="Directori docs/ existeix",
                obligatori=False,
                ok=False,
                error="No existeix directori docs/",
                suggeriment="Executar scripts/build.py per generar la web",
            ))
            return items

        # Determinar nom esperat de l'HTML
        metadata = self._carregar_metadata() or {}
        autor = self.obra_dir.parent.name
        obra = self.obra_dir.name

        # Buscar HTML generat
        html_path = docs_dir / f"{autor}-{obra}.html"
        html_existeix = html_path.exists()

        # També provar amb index dins subdirectori
        if not html_existeix:
            html_path = docs_dir / autor / obra / "index.html"
            html_existeix = html_path.exists()

        items.append(ItemValidacio(
            categoria="web",
            item="html_generat",
            descripcio="HTML generat per aquesta obra",
            obligatori=False,
            ok=html_existeix,
            error="No s'ha trobat HTML generat" if not html_existeix else None,
            suggeriment="Executar scripts/build.py per generar la web",
        ))

        # Portada copiada
        portades_dir = docs_dir / "assets" / "portades"
        portada_web = portades_dir / f"{autor}-{obra}-portada.png"
        if not portada_web.exists():
            portada_web = portades_dir / f"{autor}-{obra}-portada.jpg"

        items.append(ItemValidacio(
            categoria="web",
            item="portada_web",
            descripcio="Portada copiada a docs/assets/portades/",
            obligatori=False,
            ok=portada_web.exists(),
            error="Portada no copiada a la web" if not portada_web.exists() else None,
            suggeriment="Executar scripts/build.py per copiar la portada",
        ))

        return items

    # =========================================================================
    # VALIDACIÓ COMPLETA
    # =========================================================================

    def validar(self, memoria: "MemoriaContextual | None" = None) -> ResultatValidacio:
        """Executa totes les validacions.

        Args:
            memoria: MemoriaContextual opcional per validar coherència.

        Returns:
            ResultatValidacio amb tots els resultats.
        """
        print(f"[ValidadorFinal] Iniciant validació de {self.obra_dir}")

        tots_items: list[ItemValidacio] = []

        # ⚠️ PRIMER: Verificació d'integritat (anti-al·lucinació)
        print("[ValidadorFinal] 🛡️ Verificant integritat (anti-al·lucinació)...")
        tots_items.extend(self.validar_integritat())

        # Si integritat falla amb error crític, avortar
        errors_integritat = [i for i in tots_items if i.categoria == "integritat"
                             and i.obligatori and not i.ok]
        if errors_integritat:
            print("[ValidadorFinal] 🚨 INTEGRITAT FALLIDA — Possible al·lucinació")
            errors_critics = len(errors_integritat)
            return ResultatValidacio(
                obra_dir=str(self.obra_dir),
                timestamp=datetime.now().isoformat(),
                items=tots_items,
                errors_critics=errors_critics,
                warnings=0,
                puntuacio=0.0,
                pot_publicar=False,
                resum=f"🚨 POSSIBLE AL·LUCINACIÓ — {errors_critics} errors d'integritat. No es pot publicar.",
            )

        # Executar totes les validacions
        print("[ValidadorFinal] Validant fitxers...")
        tots_items.extend(self.validar_fitxers())

        print("[ValidadorFinal] Validant metadata...")
        tots_items.extend(self.validar_metadata())

        print("[ValidadorFinal] Validant contingut traducció...")
        tots_items.extend(self.validar_contingut_traduccio())

        print("[ValidadorFinal] Validant introducció...")
        tots_items.extend(self.validar_introduccio())

        print("[ValidadorFinal] Validant notes del traductor...")
        tots_items.extend(self.validar_notes_traductor())

        print("[ValidadorFinal] Validant glossari...")
        tots_items.extend(self.validar_glossari())

        print("[ValidadorFinal] Validant coherència...")
        tots_items.extend(self.validar_coherencia(memoria))

        print("[ValidadorFinal] Validant web...")
        tots_items.extend(self.validar_web())

        # Calcular estadístiques
        errors_critics = sum(1 for i in tots_items if i.obligatori and not i.ok)
        warnings = sum(1 for i in tots_items if not i.obligatori and not i.ok)
        total_ok = sum(1 for i in tots_items if i.ok)
        puntuacio = (total_ok / len(tots_items) * 100) if tots_items else 0

        pot_publicar = errors_critics == 0

        # Generar resum
        if pot_publicar:
            resum = f"✓ OBRA LLESTA PER PUBLICAR ({total_ok}/{len(tots_items)} checks passats)"
        else:
            resum = f"✗ {errors_critics} ERRORS CRÍTICS - No es pot publicar"

        if warnings > 0:
            resum += f" | {warnings} avisos"

        print(f"[ValidadorFinal] {resum}")

        return ResultatValidacio(
            obra_dir=str(self.obra_dir),
            timestamp=datetime.now().isoformat(),
            items=tots_items,
            errors_critics=errors_critics,
            warnings=warnings,
            puntuacio=round(puntuacio, 1),
            pot_publicar=pot_publicar,
            resum=resum,
        )

    # =========================================================================
    # INFORMES
    # =========================================================================

    def generar_informe(self, resultat: ResultatValidacio | None = None) -> str:
        """Genera un informe detallat en text.

        Args:
            resultat: ResultatValidacio previ o None per validar ara.

        Returns:
            Informe en text pla.
        """
        if resultat is None:
            resultat = self.validar()

        linies = [
            "═" * 70,
            "                    INFORME DE VALIDACIÓ",
            "═" * 70,
            f"Obra: {resultat.obra_dir}",
            f"Data: {resultat.timestamp}",
            "",
            f"Puntuació: {resultat.puntuacio:.1f}%",
            f"Errors crítics: {resultat.errors_critics}",
            f"Avisos: {resultat.warnings}",
            "",
            resultat.resum,
            "",
        ]

        # Agrupar per categoria
        categories = {}
        for item in resultat.items:
            if item.categoria not in categories:
                categories[item.categoria] = []
            categories[item.categoria].append(item)

        for cat, items in categories.items():
            linies.append("─" * 70)
            linies.append(f"  {cat.upper()}")
            linies.append("─" * 70)

            for item in items:
                if item.ok:
                    simbol = "✓"
                elif item.obligatori:
                    simbol = "✗"
                else:
                    simbol = "⚠"

                linia = f"  {simbol} {item.item}: {item.descripcio}"
                linies.append(linia)

                if not item.ok and item.error:
                    linies.append(f"      Error: {item.error}")
                if not item.ok and item.suggeriment:
                    linies.append(f"      → {item.suggeriment}")

            linies.append("")

        linies.append("═" * 70)

        return "\n".join(linies)

    def generar_informe_markdown(self, resultat: ResultatValidacio | None = None) -> str:
        """Genera un informe en format Markdown.

        Args:
            resultat: ResultatValidacio previ o None per validar ara.

        Returns:
            Informe en Markdown.
        """
        if resultat is None:
            resultat = self.validar()

        linies = [
            "# Informe de Validació",
            "",
            f"**Obra:** `{resultat.obra_dir}`",
            f"**Data:** {resultat.timestamp}",
            "",
            "## Resum",
            "",
            f"- **Puntuació:** {resultat.puntuacio:.1f}%",
            f"- **Errors crítics:** {resultat.errors_critics}",
            f"- **Avisos:** {resultat.warnings}",
            f"- **Pot publicar:** {'✓ Sí' if resultat.pot_publicar else '✗ No'}",
            "",
        ]

        # Agrupar per categoria
        categories = {}
        for item in resultat.items:
            if item.categoria not in categories:
                categories[item.categoria] = []
            categories[item.categoria].append(item)

        for cat, items in categories.items():
            linies.append(f"## {cat.title()}")
            linies.append("")
            linies.append("| Item | Descripció | Estat |")
            linies.append("|------|------------|-------|")

            for item in items:
                if item.ok:
                    estat = "✓"
                elif item.obligatori:
                    estat = "✗ **CRÍTIC**"
                else:
                    estat = "⚠ Avís"

                linies.append(f"| {item.item} | {item.descripcio} | {estat} |")

            linies.append("")

            # Errors i suggeriments
            errors = [i for i in items if not i.ok]
            if errors:
                linies.append("### Problemes detectats")
                linies.append("")
                for item in errors:
                    tipus = "**CRÍTIC**" if item.obligatori else "Avís"
                    linies.append(f"- [{tipus}] **{item.item}**: {item.error or 'Error'}")
                    if item.suggeriment:
                        linies.append(f"  - *Suggeriment:* {item.suggeriment}")
                linies.append("")

        return "\n".join(linies)
