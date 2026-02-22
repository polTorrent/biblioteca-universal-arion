"""Tests per al TraductorClassicAgent.

Avalua que l'agent tradueixi correctament textos del llatí i francès
passant mocks al mètode process.
"""

from unittest.mock import patch, MagicMock

from agents.traductor_classic import TraductorClassicAgent, SolicitutTraduccio
from agents.chunker_agent import TextChunk
from agents.base_agent import AgentResponse


def test_traductor_frances_basico():
    """Testa la traducció d'un fragment en francès simulant el LLM."""
    agent = TraductorClassicAgent()
    
    chunk = TextChunk(
        text="Il y avait une fois un roi qui vivait dans un grand château.",
        chunk_id="1",
        mida_tokens=15,
        inici_char=0,
        final_char=60
    )
    
    solicitut = SolicitutTraduccio(
        chunk=chunk,
        idioma_origen="francès",
        estil="conte clàssic"
    )

    respuesta_simulada = AgentResponse(
        content="Hi havia una vegada un rei que vivia en un gran castell.",
        metadata={"model": "venice/mock-model"}
    )
    
    with patch.object(TraductorClassicAgent, 'process', return_value=respuesta_simulada) as mock_process:
        resultat = agent.traduir_chunk(solicitut)
        
        # Validacions
        assert resultat.content == "Hi havia una vegada un rei que vivia en un gran castell."
        
        # Verificar que process s'ha cridat amb el text adequat
        args, _ = mock_process.call_args
        prompt_passat = args[0]
        assert "francès" in prompt_passat
        assert "conte clàssic" in prompt_passat
        assert "Il y avait une fois un roi" in prompt_passat


def test_traductor_llati_amb_glossari_i_calcs():
    """Testa l'aplicació del glossari i calcs al prompt passat al LLM."""
    agent = TraductorClassicAgent()
    
    chunk = TextChunk(
        text="Gallia est omnis divisa in partes tres.",
        chunk_id="2",
        mida_tokens=10,
        inici_char=0,
        final_char=39
    )
    
    solicitut = SolicitutTraduccio(
        chunk=chunk,
        idioma_origen="llatí",
        estil="històric clàssic",
        glossari_vinculat={"Gallia": "Gàl·lia"},
        calcs_a_evitar=["és tota dividida"]
    )

    respuesta_simulada = AgentResponse(
        content="Tota la Gàl·lia està dividida en tres parts.",
        metadata={"model": "venice/mock-model"}
    )
    
    with patch.object(TraductorClassicAgent, 'process', return_value=respuesta_simulada) as mock_process:
        resultat = agent.traduir_chunk(solicitut)
        
        # Validacions
        assert resultat.content == "Tota la Gàl·lia està dividida en tres parts."
        
        # Verificar components del prompt
        args, _ = mock_process.call_args
        prompt_passat = args[0]
        
        assert "TERMES DEL GLOSSARI A RESPECTAR" in prompt_passat
        assert "Gallia -> Gàl·lia" in prompt_passat
        assert "FALSOS AMICS I CALCS A EVITAR" in prompt_passat
        assert "és tota dividida" in prompt_passat
        assert "Gallia est omnis divisa in partes tres." in prompt_passat
