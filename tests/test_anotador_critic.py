"""Tests per a AnotadorCriticAgent."""

import pytest
from unittest.mock import Mock, patch

from agents.anotador_critic import (
    AnotadorCriticAgent,
    AnotacioRequest,
    NotaCritica,
)
from agents.base_agent import AgentConfig, AgentResponse


class TestNotaCritica:
    """Tests per a NotaCritica."""

    def test_nota_critica_creation(self):
        """Comprova que es pot crear una NotaCritica."""
        nota = NotaCritica(
            numero=1,
            tipus="historic",
            text_referit="Alexandre el Gran",
            nota="Rei de Macedònia (356-323 aC)",
        )
        assert nota.numero == 1
        assert nota.tipus == "historic"
        assert nota.text_referit == "Alexandre el Gran"
        assert "Macedònia" in nota.nota

    def test_tipus_options(self):
        """Comprova que tots els tipus són vàlids."""
        tipus_valids = [
            "historic",
            "cultural",
            "intertextual",
            "textual",
            "terminologic",
            "geographic",
            "prosopografic",
        ]
        for tipus in tipus_valids:
            nota = NotaCritica(
                numero=1,
                tipus=tipus,
                text_referit="Test",
                nota="Nota de test",
            )
            assert nota.tipus == tipus


class TestAnotacioRequest:
    """Tests per a AnotacioRequest."""

    def test_default_values(self):
        """Comprova valors per defecte."""
        request = AnotacioRequest(text="Text a anotar")
        assert request.text == "Text a anotar"
        assert request.text_original is None
        assert request.llengua_origen == "llati"
        assert request.genere == "narrativa"
        assert request.context_historic is None
        assert request.densitat_notes == "normal"

    def test_densitat_options(self):
        """Comprova que les densitats són vàlides."""
        for densitat in ["minima", "normal", "exhaustiva"]:
            request = AnotacioRequest(text="Test", densitat_notes=densitat)
            assert request.densitat_notes == densitat


class TestAnotadorCriticAgent:
    """Tests per a AnotadorCriticAgent."""

    def test_agent_name(self):
        """Comprova el nom de l'agent."""
        with patch.object(AnotadorCriticAgent, '__init__', lambda x, **kwargs: None):
            agent = AnotadorCriticAgent.__new__(AnotadorCriticAgent)
            assert agent.agent_name == "AnotadorCritic"

    def test_system_prompt_contains_tipus_notes(self):
        """Comprova que el system prompt conté els tipus de notes."""
        with patch.object(AnotadorCriticAgent, '__init__', lambda x, **kwargs: None):
            agent = AnotadorCriticAgent.__new__(AnotadorCriticAgent)
            prompt = agent.system_prompt
            assert "CONTEXT HISTÒRIC" in prompt
            assert "CONTEXT CULTURAL" in prompt
            assert "INTERTEXTUALITAT" in prompt
            assert "TERMINOLOGIA" in prompt

    def test_system_prompt_contains_criteri(self):
        """Comprova que el system prompt conté el criteri fonamental."""
        with patch.object(AnotadorCriticAgent, '__init__', lambda x, **kwargs: None):
            agent = AnotadorCriticAgent.__new__(AnotadorCriticAgent)
            prompt = agent.system_prompt
            assert "MENYS ÉS MÉS" in prompt

    def test_system_prompt_contains_densitat(self):
        """Comprova que el system prompt explica les densitats."""
        with patch.object(AnotadorCriticAgent, '__init__', lambda x, **kwargs: None):
            agent = AnotadorCriticAgent.__new__(AnotadorCriticAgent)
            prompt = agent.system_prompt
            assert "MÍNIMA" in prompt
            assert "NORMAL" in prompt
            assert "EXHAUSTIVA" in prompt


class TestAnotadorCriticAgentIntegration:
    """Tests d'integració (requereixen mock de l'API)."""

    @pytest.fixture
    def mock_agent(self):
        """Crea un agent amb l'API mockejada."""
        with patch('anthropic.Anthropic'):
            agent = AnotadorCriticAgent(config=AgentConfig())
            agent._logger = Mock()
            return agent

    def test_annotate_method_builds_prompt(self, mock_agent):
        """Comprova que annotate() construeix el prompt correctament."""
        mock_agent.process = Mock(return_value=AgentResponse(
            content='{"text_anotat": "Text[1]", "notes": []}',
            model="claude-sonnet-4-20250514",
            usage={"input_tokens": 100, "output_tokens": 50},
        ))

        request = AnotacioRequest(
            text="Text a anotar",
            llengua_origen="grec",
            genere="filosofia",
            densitat_notes="exhaustiva",
        )
        mock_agent.annotate(request)

        assert mock_agent.process.called
        prompt_arg = mock_agent.process.call_args[0][0]
        assert "LLENGUA ORIGEN: grec" in prompt_arg
        assert "GÈNERE: filosofia" in prompt_arg
        assert "DENSITAT DESITJADA: exhaustiva" in prompt_arg

    def test_annotate_with_context(self, mock_agent):
        """Comprova que el context s'inclou al prompt."""
        mock_agent.process = Mock(return_value=AgentResponse(
            content='{"text_anotat": "Text", "notes": []}',
            model="claude-sonnet-4-20250514",
            usage={"input_tokens": 100, "output_tokens": 50},
        ))

        request = AnotacioRequest(
            text="Text",
            context_historic="Atenes, segle V aC",
        )
        mock_agent.annotate(request)

        prompt_arg = mock_agent.process.call_args[0][0]
        assert "CONTEXT HISTÒRIC CONEGUT" in prompt_arg
        assert "Atenes" in prompt_arg
