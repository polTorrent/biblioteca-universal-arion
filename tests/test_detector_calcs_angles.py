"""Tests per al detector de calcs de l'anglès.

Verifica que el detector identifica correctament calcs sintàctics
i lèxics típics de traduccions de l'anglès al català.
"""

import pytest
from utils.detector_calcs import detectar_calcs, TipusCalc


class TestDetectorCalcsAngles:
    """Tests per a calcs de l'anglès."""

    def test_detecta_per_totes_les_aparences(self):
        """'Per totes les aparences' és un calc de 'By all appearances'."""
        text = "Per totes les aparences havia estat abandonat."
        resultat = detectar_calcs(text, "anglès")

        assert len(resultat.calcs) == 1
        assert "Per totes les aparences" in resultat.calcs[0].text_original
        assert resultat.calcs[0].severitat >= 6.0

    def test_detecta_mes_aviat_que_no_pas(self):
        """'més aviat que no pas' és un calc de 'rather than'."""
        text = "Volia caminar més aviat que no pas córrer."
        resultat = detectar_calcs(text, "anglès")

        assert len(resultat.calcs) == 1
        assert "més aviat que no pas" in resultat.calcs[0].text_original

    def test_detecta_vaig_manar(self):
        """'vaig manar' (to bid/command) hauria de ser 'vaig demanar'."""
        text = "Vaig manar a Pedro que tanqués la porta."
        resultat = detectar_calcs(text, "anglès")

        assert len(resultat.calcs) == 1
        assert "manar" in resultat.calcs[0].text_original.lower()

    def test_detecta_repeticio_adverbi(self):
        """Repeticions d'adverbis (Long—long) són calcs de l'anglès."""
        text = "Llargament—llargament vaig llegir."
        resultat = detectar_calcs(text, "anglès")

        assert len(resultat.calcs) == 1
        assert "Llargament—llargament" in resultat.calcs[0].text_original

    def test_detecta_just_verb(self):
        """'just + verb' (just becoming) és un calc."""
        text = "El retrat d'una jove que just esdevenia dona."
        resultat = detectar_calcs(text, "anglès")

        calcs_just = [c for c in resultat.calcs if "just" in c.text_original.lower()]
        assert len(calcs_just) >= 1

    def test_detecta_lexic_forcat(self):
        """Detecta lèxic forçat: vivaces, fornícula, esquinçades."""
        text = "Les decoracions eren vivaces i esquinçades. Hi havia una fornícula."
        resultat = detectar_calcs(text, "anglès")

        # Hauria de detectar almenys 2 d'aquests
        termes_detectats = [c.text_original.lower() for c in resultat.calcs]
        trobats = sum(1 for t in ["vivaces", "esquinçades", "fornícula"]
                      if any(t in d for d in termes_detectats))
        assert trobats >= 2

    def test_puntuacio_baixa_amb_molts_calcs(self):
        """Amb 8+ calcs, la puntuació ha de ser <= 5.5."""
        text = """
        Per totes les aparences havia estat abandonat.
        Vaig manar a Pedro que tanqués les portes.
        Era més aviat que no pas sortir.
        Llargament—llargament vaig llegir.
        Just esdevenia dona.
        Decoracions vivaces i esquinçades.
        Una fornícula petita.
        """ * 50  # Repetir per tenir més text

        resultat = detectar_calcs(text, "anglès")

        # Amb molts calcs, puntuació ha de ser baixa
        if len(resultat.calcs) >= 8:
            assert resultat.puntuacio_fluidesa <= 5.5

    def test_puntuacio_alta_sense_calcs(self):
        """Text net ha de tenir puntuació 10.0."""
        text = """
        El castell era una construcció ombrívola. Tot indicava que havia
        estat abandonat feia poc. Les parets estaven cobertes de tapissos.
        """
        resultat = detectar_calcs(text, "anglès")

        assert len(resultat.calcs) == 0
        assert resultat.puntuacio_fluidesa == 10.0

    def test_densitat_afecta_puntuacio(self):
        """Textos llargs amb pocs calcs han de tenir millor puntuació que curts amb mateixos calcs."""
        text_curt = "Per totes les aparences estava malalt."
        text_llarg = "Per totes les aparences estava malalt. " + " ".join(["Frase normal sense cap problema."] * 50)

        resultat_curt = detectar_calcs(text_curt, "anglès")
        resultat_llarg = detectar_calcs(text_llarg, "anglès")

        # El text llarg ha de tenir millor puntuació (menor densitat)
        assert resultat_llarg.puntuacio_fluidesa > resultat_curt.puntuacio_fluidesa


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
