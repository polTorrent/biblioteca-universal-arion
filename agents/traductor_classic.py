"""Agent traductor clàssic per a textos grecollatins i literatura clàssica."""

from pydantic import BaseModel, Field

from agents.base_agent import AgentConfig, AgentResponse, BaseAgent
from agents.chunker_agent import TextChunk


class SolicitutTraduccio(BaseModel):
    """Estil i metadades per a la traducció d'un fragment."""
    chunk: TextChunk
    idioma_origen: str = "llatí"
    estil: str = "clàssic i literari"
    context_previ: str = ""
    glossari_vinculat: dict = Field(default_factory=dict)  # Per a futura injecció de regles
    calcs_a_evitar: list[str] = Field(default_factory=list)  # Per a futura prevenció automàtica


class TraductorClassicAgent(BaseAgent):
    """Agent especialitzat en la traducció literària acurada de textos clàssics al català."""

    agent_name: str = "TraductorClassic"
    fallback_model: str = "venice/zai-org-glm-5" # Si s'estableix un ús més complex

    @property
    def system_prompt(self) -> str:
        return """Ets un traductor expert en literatura clàssica i llengües antigues (llatí, grec) i modernes (francès, alemany, anglès, japonès, xinès). 
La teva missió és traduir narrativa, filosofia i teatre clàssic al català amb un registre literari ric, escollit, precís i natural, evitant calcs estructurals o semàntics. 

DIRECTRIUS DE TRADUCCIÓ:
1. Màxima fidelitat a l'original sense sacrificar la naturalitat de la llengua catalana.
2. Evita transliteracions sintàctiques directes (ex: abusar d'ablatius absoluts llatins, passives pesades, o l'ordre V-S-O alemany confús).
3. Utilitza un vocabulari propi de grans traductors com Carles Riba, Joan F. Mira o Bernat Metge: ric, culte, però comprensible.
4. Preserva les figures retòriques i el to (solemne, satíric, dramàtic) de l'autor original.

Has de retornar estretament el text traduït de la porció enviada sense començar amb introduccions com "Aquesta és la traducció" o similars."""

    def traduir_chunk(self, solicitut: SolicitutTraduccio) -> AgentResponse:
        """Tradueix un fragment (chunk) al català amb estil literari."""
        
        prompt_parts = [
            f"Fes una traducció literària de l'idioma '{solicitut.idioma_origen}' al català, mantenint un estil {solicitut.estil}.",
            "Pots basar-te en aquest context previ per comprendre l'escena:" if solicitut.context_previ else "",
            f"CONTEXT PREVI: {solicitut.context_previ[-500:]}" if solicitut.context_previ else "",
        ]
        
        if solicitut.glossari_vinculat:
            prompt_parts.append("\nTERMES DEL GLOSSARI A RESPECTAR (TRADUCCIONS FORÇADES):")
            for terme, dades in solicitut.glossari_vinculat.items():
                traduccio = dades if isinstance(dades, str) else dades.get("traduccio_catalana", "...")
                prompt_parts.append(f"- {terme} -> {traduccio}")

        if solicitut.calcs_a_evitar:
            prompt_parts.append("\nFALSOS AMICS I CALCS A EVITAR (No utilitzis aquestes combinacions):")
            for calc in solicitut.calcs_a_evitar:
                prompt_parts.append(f"- {calc}")
                
        prompt_parts.append(f"\nTEXT A TRADUIR:\n{solicitut.chunk.text}")

        # Retornem exclusivament el processament del text, sense estructures JSON tret que ho requereixi el pipeline v2
        return self.process("\n".join(filter(None, prompt_parts)))
