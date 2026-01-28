"""Tests per a PerfeccionamentAgent."""

import pytest
from unittest.mock import Mock, patch

from agents.perfeccionament_agent import (
    PerfeccionamentAgent,
    PerfeccionamentRequest,
)
from agents.base_agent import AgentConfig, AgentResponse


class TestPerfeccionamentRequest:
    """Tests per a PerfeccionamentRequest."""

    def test_default_values(self):
        """Comprova valors per defecte."""
        request = PerfeccionamentRequest(text="Hola món")
        assert request.text == "Hola món"
        assert request.text_original is None
        assert request.llengua_origen == "llati"
        assert request.genere == "narrativa"
        assert request.glossari is None
        assert request.nivell == "normal"

    def test_all_values(self):
        """Comprova que accepta tots els valors."""
        request = PerfeccionamentRequest(
            text="Text traduït",
            text_original="Original text",
            llengua_origen="japonès",
            genere="poesia",
            glossari={"terme": "traducció"},
            nivell="intensiu",
        )
        assert request.text == "Text traduït"
        assert request.text_original == "Original text"
        assert request.llengua_origen == "japonès"
        assert request.genere == "poesia"
        assert request.glossari == {"terme": "traducció"}
        assert request.nivell == "intensiu"

    def test_nivell_options(self):
        """Comprova que els nivells són vàlids."""
        for nivell in ["lleuger", "normal", "intensiu"]:
            request = PerfeccionamentRequest(text="Test", nivell=nivell)
            assert request.nivell == nivell


class TestPerfeccionamentAgent:
    """Tests per a PerfeccionamentAgent."""

    def test_agent_name(self):
        """Comprova el nom de l'agent."""
        with patch.object(PerfeccionamentAgent, '__init__', lambda x, **kwargs: None):
            agent = PerfeccionamentAgent.__new__(PerfeccionamentAgent)
            assert agent.agent_name == "Perfeccionament"

    def test_system_prompt_contains_naturalitzacio(self):
        """Comprova que el system prompt conté secció de naturalització."""
        with patch.object(PerfeccionamentAgent, '__init__', lambda x, **kwargs: None):
            agent = PerfeccionamentAgent.__new__(PerfeccionamentAgent)
            prompt = agent.system_prompt
            assert "NATURALITZACIÓ" in prompt
            assert "JAPONÈS" in prompt
            assert "LLATÍ" in prompt
            assert "GREC" in prompt

    def test_system_prompt_contains_normativa(self):
        """Comprova que el system prompt conté secció de normativa."""
        with patch.object(PerfeccionamentAgent, '__init__', lambda x, **kwargs: None):
            agent = PerfeccionamentAgent.__new__(PerfeccionamentAgent)
            prompt = agent.system_prompt
            assert "NORMATIVA CATALANA" in prompt
            assert "IEC" in prompt

    def test_system_prompt_contains_estil(self):
        """Comprova que el system prompt conté secció d'estil."""
        with patch.object(PerfeccionamentAgent, '__init__', lambda x, **kwargs: None):
            agent = PerfeccionamentAgent.__new__(PerfeccionamentAgent)
            prompt = agent.system_prompt
            assert "ESTIL I VEU" in prompt
            assert "FILOSOFIA" in prompt
            assert "POESIA" in prompt

    def test_system_prompt_priority(self):
        """Comprova que el system prompt conté la prioritat correcta."""
        with patch.object(PerfeccionamentAgent, '__init__', lambda x, **kwargs: None):
            agent = PerfeccionamentAgent.__new__(PerfeccionamentAgent)
            prompt = agent.system_prompt
            assert "VEU DE L'AUTOR" in prompt
            assert "FLUÏDESA" in prompt
            assert "NORMATIVA ESTRICTA" in prompt


class TestPerfeccionamentAgentIntegration:
    """Tests d'integració (requereixen mock de l'API)."""

    @pytest.fixture
    def mock_agent(self):
        """Crea un agent amb l'API mockejada."""
        with patch('anthropic.Anthropic'):
            agent = PerfeccionamentAgent(config=AgentConfig())
            agent._logger = Mock()
            return agent

    def test_perfect_method_builds_prompt(self, mock_agent):
        """Comprova que perfect() construeix el prompt correctament."""
        mock_agent.process = Mock(return_value=AgentResponse(
            content='{"text_perfeccionat": "Text perfeccionat"}',
            model="claude-sonnet-4-20250514",
            usage={"input_tokens": 100, "output_tokens": 50},
        ))

        request = PerfeccionamentRequest(
            text="Text a perfeccionar",
            llengua_origen="llatí",
            genere="filosofia",
            nivell="normal",
        )
        mock_agent.perfect(request)

        # Verificar que process es va cridar amb el prompt correcte
        assert mock_agent.process.called
        prompt_arg = mock_agent.process.call_args[0][0]
        assert "LLENGUA ORIGEN: llatí" in prompt_arg
        assert "GÈNERE: filosofia" in prompt_arg
        assert "NIVELL: normal" in prompt_arg
        assert "Text a perfeccionar" in prompt_arg

    def test_perfect_with_glossari(self, mock_agent):
        """Comprova que el glossari s'inclou al prompt."""
        mock_agent.process = Mock(return_value=AgentResponse(
            content='{"text_perfeccionat": "Text"}',
            model="claude-sonnet-4-20250514",
            usage={"input_tokens": 100, "output_tokens": 50},
        ))

        request = PerfeccionamentRequest(
            text="Text",
            glossari={"logos": "raó"},
        )
        mock_agent.perfect(request)

        prompt_arg = mock_agent.process.call_args[0][0]
        assert "GLOSSARI A RESPECTAR" in prompt_arg
        assert "logos" in prompt_arg

    def test_perfect_with_original(self, mock_agent):
        """Comprova que el text original s'inclou al prompt."""
        mock_agent.process = Mock(return_value=AgentResponse(
            content='{"text_perfeccionat": "Text"}',
            model="claude-sonnet-4-20250514",
            usage={"input_tokens": 100, "output_tokens": 50},
        ))

        request = PerfeccionamentRequest(
            text="Traducció",
            text_original="Original latin text",
        )
        mock_agent.perfect(request)

        prompt_arg = mock_agent.process.call_args[0][0]
        assert "TEXT ORIGINAL (per referència)" in prompt_arg
        assert "Original latin text" in prompt_arg
