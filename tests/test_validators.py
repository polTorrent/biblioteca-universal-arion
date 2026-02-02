"""Tests per al mòdul utils/validators.py."""

import pytest
from utils.validators import (
    validar_text_entrada,
    netejar_text,
    validar_glossari,
    validar_metadata,
    SeverityLevel,
    ValidationResult,
)


class TestValidarTextEntrada:
    """Tests per a validar_text_entrada."""

    def test_text_valid(self):
        """Un text vàlid hauria de passar la validació."""
        text = "Aquest és un text de prova suficientment llarg per passar la validació."
        result = validar_text_entrada(text, "català")
        assert result.valid
        assert not result.has_errors()

    def test_text_buit(self):
        """Un text buit hauria de fallar."""
        result = validar_text_entrada("", "català")
        assert not result.valid
        assert result.has_errors()

    def test_text_massa_curt(self):
        """Un text massa curt hauria de fallar."""
        result = validar_text_entrada("Hola", "català")
        assert not result.valid
        assert result.has_errors()

    def test_text_massa_llarg(self):
        """Un text massa llarg hauria de generar error."""
        text = "a" * 150_000
        result = validar_text_entrada(text, "català", max_chars=100_000)
        assert not result.valid
        assert result.has_errors()

    def test_text_llarg_warning(self):
        """Un text molt llarg (però dins límit) hauria de generar warning."""
        text = "a" * 85_000
        result = validar_text_entrada(text, "català", max_chars=100_000)
        assert result.valid  # Passa però amb warning
        assert result.has_warnings()

    def test_llengua_incorrecta_warning(self):
        """Si el text no sembla la llengua declarada, warning."""
        # Text en anglès però declarat com a grec
        text = "The quick brown fox jumps over the lazy dog. " * 5
        result = validar_text_entrada(text, "grec")
        assert result.valid  # Passa però amb warning
        assert result.has_warnings()

    def test_caracters_control(self):
        """Caràcters de control haurien de generar warning."""
        text = "Text vàlid amb caràcters de control\x00\x01\x02 més text aquí."
        result = validar_text_entrada(text, "català")
        # NULL genera error, altres generen warning
        assert not result.valid  # NULL és error

    def test_tipus_incorrecte(self):
        """Un tipus no-string hauria de fallar."""
        result = validar_text_entrada(123, "català")  # type: ignore
        assert not result.valid
        assert result.has_errors()


class TestNetejarText:
    """Tests per a netejar_text."""

    def test_netejar_basic(self):
        """Neteja bàsica d'un text."""
        text = "  Hola món  "
        result = netejar_text(text)
        assert result == "Hola món"

    def test_netejar_caracters_control(self):
        """Elimina caràcters de control."""
        text = "Text\x00amb\x01control\x02"
        result = netejar_text(text)
        assert "\x00" not in result
        assert "\x01" not in result
        assert "Text" in result

    def test_normalitzar_espais(self):
        """Normalitza espais múltiples."""
        text = "Text  amb   molts    espais"
        result = netejar_text(text)
        assert "  " not in result

    def test_normalitzar_salts_linia(self):
        """Normalitza salts de línia múltiples."""
        text = "Paràgraf 1\n\n\n\n\nParàgraf 2"
        result = netejar_text(text)
        assert "\n\n\n" not in result
        assert "Paràgraf 1\n\nParàgraf 2" == result


class TestValidarGlossari:
    """Tests per a validar_glossari."""

    def test_glossari_valid(self):
        """Un glossari vàlid hauria de passar."""
        glossari = {
            "termes": [
                {"id": "term1", "traduccio": "traducció1"},
                {"id": "term2", "traduccio": "traducció2"},
            ]
        }
        result = validar_glossari(glossari)
        assert result.valid

    def test_glossari_buit(self):
        """Un glossari buit genera warning."""
        glossari = {"termes": []}
        result = validar_glossari(glossari)
        assert result.valid  # Passa amb warning
        assert result.has_warnings()

    def test_glossari_id_duplicat(self):
        """IDs duplicats generen warning."""
        glossari = [
            {"id": "term1", "traduccio": "traducció1"},
            {"id": "term1", "traduccio": "traducció2"},  # Duplicat
        ]
        result = validar_glossari(glossari)
        assert result.has_warnings()

    def test_glossari_format_invalid(self):
        """Format invàlid genera error."""
        result = validar_glossari("no és un diccionari")  # type: ignore
        assert not result.valid


class TestValidarMetadata:
    """Tests per a validar_metadata."""

    def test_metadata_valid(self):
        """Metadata vàlid hauria de passar."""
        metadata = {
            "titol": "L'obra",
            "autor": "L'autor",
            "llengua_origen": "llatí",
            "any_original": -44,
            "genere": "filosofia",
            "estat": "en_progres",
        }
        result = validar_metadata(metadata)
        assert result.valid

    def test_metadata_camps_requerits(self):
        """Sense camps requerits hauria de fallar."""
        metadata = {"genere": "narrativa"}  # Falta titol, autor, llengua
        result = validar_metadata(metadata)
        assert not result.valid

    def test_metadata_camps_recomanats(self):
        """Sense camps recomanats genera warning."""
        metadata = {
            "titol": "L'obra",
            "autor": "L'autor",
            "llengua_origen": "llatí",
            # Falta any_original, genere, estat
        }
        result = validar_metadata(metadata)
        assert result.valid  # Passa amb warnings
        assert result.has_warnings()


class TestValidationResult:
    """Tests per a ValidationResult."""

    def test_summary_ok(self):
        """Resum d'una validació correcta."""
        result = ValidationResult(valid=True, messages=[])
        assert "✅" in result.summary()

    def test_summary_errors(self):
        """Resum amb errors."""
        result = ValidationResult(
            valid=False,
            messages=[(SeverityLevel.ERROR, "Error de prova")]
        )
        assert "❌" in result.summary()

    def test_summary_warnings(self):
        """Resum amb warnings."""
        result = ValidationResult(
            valid=True,
            messages=[(SeverityLevel.WARNING, "Warning de prova")]
        )
        assert "⚠️" in result.summary()

    def test_str(self):
        """__str__ retorna summary."""
        result = ValidationResult(valid=True, messages=[])
        assert str(result) == result.summary()
