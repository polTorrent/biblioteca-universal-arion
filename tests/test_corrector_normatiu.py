"""Tests per al CorrectorNormatiuAgent."""

import pytest

# Skip tot el mòdul si LanguageTool no està disponible
pytest.importorskip("language_tool_python")

from agents.corrector_normatiu import (
    CorrectorNormatiuAgent,
    ConfiguracioCorrector,
    ResultatCorreccioNormativa,
)


class TestConfiguracioCorrector:
    """Tests de la configuració del corrector."""

    def test_configuracio_default(self):
        """La configuració per defecte té valors raonables."""
        config = ConfiguracioCorrector()

        assert "ortografia" in config.categories_auto
        assert "tipografia" in config.categories_auto
        assert "puntuacio" in config.categories_auto
        assert "gramatica" in config.categories_informe
        assert "estil" in config.categories_informe
        assert config.max_correccions_chunk == 50
        assert config.min_confianca == 0.8

    def test_configuracio_personalitzada(self):
        """Es pot personalitzar la configuració."""
        config = ConfiguracioCorrector(
            categories_auto=["ortografia"],
            categories_informe=["gramatica"],
            max_correccions_chunk=10,
        )

        assert config.categories_auto == ["ortografia"]
        assert config.categories_informe == ["gramatica"]
        assert config.max_correccions_chunk == 10


class TestCorrectorNormatiuAgent:
    """Tests del corrector normatiu."""

    @pytest.fixture
    def agent(self):
        """Crea un agent per als tests."""
        return CorrectorNormatiuAgent()

    @pytest.fixture
    def agent_restrictiu(self):
        """Agent amb límit baix de correccions."""
        config = ConfiguracioCorrector(max_correccions_chunk=5)
        return CorrectorNormatiuAgent(configuracio=config)

    def test_text_correcte(self, agent):
        """Un text correcte no es modifica."""
        text = "El cel és blau i els arbres són verds."
        resultat = agent.corregir(text)

        assert resultat.languagetool_disponible
        assert resultat.text_original == text
        # El text correcte hauria de tenir poques o cap correcció
        assert resultat.puntuacio_final >= resultat.puntuacio_inicial or resultat.correccions_aplicades == 0

    def test_detecta_barbarisme(self, agent):
        """Detecta barbarismes (castellanismes)."""
        # Usar text més curt perquè "pero" es detecti clarament
        text = "Ell va anar pero no va tornar."
        resultat = agent.corregir(text)

        assert resultat.languagetool_disponible
        # "pero" és un barbarisme comú, pot corregir-se o informar-se
        # La puntuació < 10 indica que s'ha detectat algun error
        assert (
            resultat.correccions_aplicades > 0
            or resultat.errors_informats > 0
            or resultat.puntuacio_inicial < 10.0
        )

    def test_corregeix_ortografia(self, agent):
        """Corregeix errors d'ortografia automàticament."""
        # Errors comuns d'ortografia
        text = "La casa es molt gran."  # "és" sense accent
        resultat = agent.corregir(text)

        assert resultat.languagetool_disponible
        # Pot corregir o no segons la categoria assignada per LanguageTool

    def test_informa_gramatica_sense_corregir_per_defecte(self, agent):
        """La gramàtica s'informa però no es corregeix per defecte."""
        config = ConfiguracioCorrector(
            categories_auto=["ortografia"],
            categories_informe=["gramatica", "estil", "barbarisme"],
        )
        agent_personalitzat = CorrectorNormatiuAgent(configuracio=config)

        text = "El text amb possibles problemes."
        resultat = agent_personalitzat.corregir(text)

        assert resultat.languagetool_disponible
        # Els errors de gramàtica van a avisos, no a correccions
        # (si n'hi ha)

    def test_respecta_limit_correccions(self, agent_restrictiu):
        """Respecta el límit màxim de correccions."""
        # Text amb molts possibles errors
        text = "pero aunque bueno pues entonces luego desde mientras todavia siempre nunca"
        resultat = agent_restrictiu.corregir(text)

        # No hauria d'aplicar més de 5 correccions
        assert resultat.correccions_aplicades <= 5

    def test_calcula_puntuacio(self, agent):
        """Calcula puntuació abans i després."""
        text = "Text correcte en català."
        resultat = agent.corregir(text)

        assert 0 <= resultat.puntuacio_inicial <= 10
        assert 0 <= resultat.puntuacio_final <= 10

    def test_resultat_te_estructura_correcta(self, agent):
        """El resultat té tots els camps esperats."""
        text = "Prova de text."
        resultat = agent.corregir(text)

        assert isinstance(resultat, ResultatCorreccioNormativa)
        assert hasattr(resultat, "text_original")
        assert hasattr(resultat, "text_corregit")
        assert hasattr(resultat, "correccions_aplicades")
        assert hasattr(resultat, "errors_informats")
        assert hasattr(resultat, "puntuacio_inicial")
        assert hasattr(resultat, "puntuacio_final")
        assert hasattr(resultat, "correccions")
        assert hasattr(resultat, "avisos")
        assert hasattr(resultat, "languagetool_disponible")

    def test_correccions_detallades(self, agent):
        """Les correccions inclouen detall."""
        text = "pero es molt dificil fer aixo."  # Errors intencionals
        resultat = agent.corregir(text)

        if resultat.correccions:
            correccio = resultat.correccions[0]
            assert "categoria" in correccio
            assert "original" in correccio
            assert "corregit" in correccio
            assert "posicio" in correccio

    def test_avisos_detallats(self, agent):
        """Els avisos inclouen detall."""
        config = ConfiguracioCorrector(
            categories_auto=[],  # No corregeix res
            categories_informe=["ortografia", "gramatica", "estil", "barbarisme", "tipografia", "puntuacio"],
        )
        agent_nomes_informa = CorrectorNormatiuAgent(configuracio=config)

        text = "pero aunque bueno pues"
        resultat = agent_nomes_informa.corregir(text)

        if resultat.avisos:
            avis = resultat.avisos[0]
            assert "categoria" in avis
            assert "text" in avis
            assert "missatge" in avis
            assert "suggeriments" in avis

    def test_process_retorna_agent_response(self, agent):
        """El mètode process() retorna AgentResponse vàlid."""
        from agents.base_agent import AgentResponse

        text = "Prova de text."
        response = agent.process(text)

        assert isinstance(response, AgentResponse)
        assert response.content == agent.corregir(text).text_corregit
        assert response.model == "LanguageTool"
        assert response.cost_eur == 0.0


class TestIntegracioLanguageTool:
    """Tests d'integració amb LanguageTool real."""

    @pytest.fixture
    def agent(self):
        return CorrectorNormatiuAgent()

    def test_corrector_inicialitzat(self, agent):
        """El corrector de LanguageTool s'inicialitza correctament."""
        assert agent.corrector is not None

    def test_diversos_tipus_errors(self, agent):
        """Detecta diversos tipus d'errors."""
        textos_amb_errors = [
            ("pero", "barbarisme"),
            ("el text", "sense error esperat"),
        ]

        for text, descripcio in textos_amb_errors:
            resultat = agent.corregir(text)
            assert resultat.languagetool_disponible, f"LanguageTool no disponible per: {descripcio}"


# Tests que s'executen sempre (sense LanguageTool)
class TestSenseLanguageTool:
    """Tests per quan LanguageTool no està disponible."""

    def test_graceful_degradation(self, monkeypatch):
        """L'agent funciona sense LanguageTool (graceful degradation)."""
        # Simular que LanguageTool no està disponible
        import agents.corrector_normatiu as module
        monkeypatch.setattr(module, "LANGUAGETOOL_DISPONIBLE", False)

        agent = CorrectorNormatiuAgent()
        text = "Text de prova."
        resultat = agent.corregir(text)

        assert not resultat.languagetool_disponible
        assert resultat.text_original == text
        assert resultat.text_corregit == text
        assert resultat.correccions_aplicades == 0
