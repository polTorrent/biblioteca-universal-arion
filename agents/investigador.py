"""Agent Investigador per recollir context històric i cultural.

S'executa abans de la traducció per proporcionar:
- Biografia de l'autor
- Context històric de l'obra
- Influències i tradició literària
- Temes principals
- Notes per a l'anotador crític
"""

from typing import Any

from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent, AgentConfig, AgentResponse, extract_json_from_text
from core import MemoriaContextual, ContextInvestigacio


# =============================================================================
# MODELS
# =============================================================================

class InformeInvestigacio(BaseModel):
    """Resultat de la investigació."""

    # Autor
    autor_nom_complet: str = ""
    autor_dates: str = ""  # ex: "4 a.C. - 65 d.C."
    autor_origen: str = ""  # ex: "Còrdova, Hispània"
    autor_bio_breu: str = ""  # 2-3 frases
    autor_context_historic: str = ""  # Època, situació política
    autor_influencies: list[str] = Field(default_factory=list)
    autor_estil: str = ""  # Característiques de l'estil literari

    # Obra
    obra_titol_original: str = ""
    obra_data_composicio: str = ""  # ex: "c. 49 d.C."
    obra_genere: str = ""  # ex: "diàleg filosòfic", "epístola"
    obra_context_creacio: str = ""  # Circumstàncies de creació
    obra_temes_principals: list[str] = Field(default_factory=list)
    obra_estructura: str = ""  # Descripció de l'estructura
    obra_recepcio: str = ""  # Recepció històrica

    # Per l'Anotador
    personatges_mencions: list[str] = Field(default_factory=list)
    referencies_culturals: list[str] = Field(default_factory=list)
    termes_tecnics: list[str] = Field(default_factory=list)

    # Metadades
    fonts_consultades: list[str] = Field(default_factory=list)
    fiabilitat: float = 0.0  # 0-10, autoavaluació de la qualitat de la info


# =============================================================================
# AGENT
# =============================================================================

class InvestigadorAgent(BaseAgent):
    """Agent que investiga l'autor i l'obra abans de traduir.

    Exemple d'ús:
        from agents.investigador import InvestigadorAgent
        from core import MemoriaContextual

        agent = InvestigadorAgent()
        memoria = MemoriaContextual()

        informe = agent.investigar(
            autor="Sèneca",
            obra="De Brevitate Vitae",
            llengua_origen="llatí",
            memoria=memoria,
        )

        print(informe.autor_bio_breu)
        print(memoria.generar_context_per_traductor())
    """

    agent_name = "Investigador"

    SYSTEM_PROMPT = '''Ets un investigador acadèmic especialitzat en literatura clàssica i història antiga.

La teva tasca és recollir informació precisa i verificable sobre autors i obres per ajudar en traduccions acadèmiques al català.

INSTRUCCIONS:
1. Proporciona només informació VERIFICADA i PRECISA
2. Si no estàs segur d'alguna cosa, indica-ho clarament amb "incert" o deixa el camp buit
3. Prioritza informació de fonts acadèmiques i enciclopèdiques
4. Inclou dates i llocs quan sigui possible
5. Identifica temes, personatges i referències que requeriran notes explicatives
6. El contingut ha de ser útil per a un traductor acadèmic

FORMAT DE RESPOSTA:
Respon SEMPRE en JSON vàlid amb EXACTAMENT aquesta estructura:
{
    "autor_nom_complet": "nom complet de l'autor",
    "autor_dates": "dates de vida (ex: 4 a.C. - 65 d.C.)",
    "autor_origen": "lloc d'origen",
    "autor_bio_breu": "biografia breu de 2-3 frases",
    "autor_context_historic": "context històric de l'època",
    "autor_influencies": ["influència 1", "influència 2"],
    "autor_estil": "característiques del seu estil literari",
    "obra_titol_original": "títol original complet",
    "obra_data_composicio": "data de composició",
    "obra_genere": "gènere literari",
    "obra_context_creacio": "circumstàncies de creació",
    "obra_temes_principals": ["tema 1", "tema 2", "tema 3"],
    "obra_estructura": "descripció de l'estructura",
    "obra_recepcio": "recepció històrica",
    "personatges_mencions": ["personatge 1", "personatge 2"],
    "referencies_culturals": ["referència 1", "referència 2"],
    "termes_tecnics": ["terme 1", "terme 2"],
    "fonts_consultades": ["font 1", "font 2"],
    "fiabilitat": 8.5
}

IMPORTANT: Respon NOMÉS amb el JSON, sense text addicional abans o després.
'''

    def __init__(
        self,
        config: AgentConfig | None = None,
        logger: Any = None,
    ) -> None:
        """Inicialitza l'agent investigador.

        Args:
            config: Configuració de l'agent.
            logger: Logger opcional.
        """
        config = config or AgentConfig(
            temperature=0.3,  # Baix per precisió factual
            max_tokens=4000,
        )
        super().__init__(config, logger)

    @property
    def system_prompt(self) -> str:
        """Retorna el system prompt de l'agent."""
        return self.SYSTEM_PROMPT

    def investigar(
        self,
        autor: str,
        obra: str,
        llengua_origen: str = "llatí",
        text_mostra: str = "",
        memoria: MemoriaContextual | None = None,
    ) -> InformeInvestigacio:
        """Investiga l'autor i l'obra.

        Args:
            autor: Nom de l'autor.
            obra: Títol de l'obra.
            llengua_origen: Llengua original (llatí, grec, etc.).
            text_mostra: Fragment del text per context (opcional).
            memoria: Memòria contextual per guardar resultats (opcional).

        Returns:
            InformeInvestigacio amb tota la informació recollida.
        """
        self.logger.log_info(self.agent_name, f"Investigant: {autor} - {obra}")

        prompt = self._construir_prompt(autor, obra, llengua_origen, text_mostra)

        try:
            # Cridar al model
            resposta = self.process(prompt)
            contingut = resposta.content

            # Parsejar JSON de la resposta
            informe = self._parsejar_resposta(contingut, autor, obra)

            # Guardar a memòria contextual si existeix
            if memoria:
                self._guardar_a_memoria(informe, memoria)

            self.logger.log_info(
                self.agent_name,
                f"✅ Investigació completada - Fiabilitat: {informe.fiabilitat}/10"
            )
            return informe

        except Exception as e:
            self.logger.log_error(self.agent_name, f"Error en investigació: {e}")
            return InformeInvestigacio(
                autor_nom_complet=autor,
                obra_titol_original=obra,
                fiabilitat=0.0,
            )

    def _construir_prompt(
        self,
        autor: str,
        obra: str,
        llengua_origen: str,
        text_mostra: str,
    ) -> str:
        """Construeix el prompt per a la investigació."""
        prompt = f'''Investiga l'autor i l'obra següents per preparar una traducció acadèmica al català.

AUTOR: {autor}
OBRA: {obra}
LLENGUA ORIGINAL: {llengua_origen}
'''

        if text_mostra:
            prompt += f'''
MOSTRA DEL TEXT (primers 500 caràcters):
{text_mostra[:500]}
'''

        prompt += '''
Proporciona informació detallada i precisa sobre:

1. L'AUTOR:
   - Nom complet i dates (naixement - mort)
   - Lloc d'origen
   - Breu biografia (2-3 frases)
   - Context històric (època, situació política, cultural)
   - Influències literàries i filosòfiques
   - Característiques del seu estil

2. L'OBRA:
   - Títol original complet
   - Data de composició (aproximada si cal)
   - Gènere literari
   - Circumstàncies de creació (a qui va dedicada, per què es va escriure)
   - Temes principals (3-5 temes)
   - Estructura general
   - Recepció històrica i importància

3. PER A L'ANOTADOR CRÍTIC:
   - Personatges històrics o mitològics que puguin aparèixer a l'obra
   - Referències culturals que requeriran explicació per al lector modern
   - Termes tècnics o filosòfics importants de l'obra

4. FONTS:
   - On pot trobar més informació un traductor acadèmic

Respon en JSON amb l'estructura especificada.
'''
        return prompt

    def _parsejar_resposta(
        self,
        contingut: str,
        autor: str,
        obra: str,
    ) -> InformeInvestigacio:
        """Parseja la resposta del model a InformeInvestigacio."""
        try:
            # Intentar extreure JSON de la resposta
            dades = extract_json_from_text(contingut)

            if dades:
                # Validar i crear informe
                return InformeInvestigacio(**dades)
            else:
                # Si no hi ha JSON, crear informe bàsic
                self.logger.log_warning(
                    self.agent_name,
                    "No s'ha trobat JSON vàlid, creant informe bàsic"
                )
                return self._crear_informe_basic(autor, obra, contingut)

        except Exception as e:
            self.logger.log_warning(
                self.agent_name,
                f"Error parsejant resposta: {e}"
            )
            return self._crear_informe_basic(autor, obra, contingut)

    def _crear_informe_basic(
        self,
        autor: str,
        obra: str,
        text_resposta: str,
    ) -> InformeInvestigacio:
        """Crea un informe bàsic a partir de text no estructurat."""
        # Intentar extreure alguna informació del text
        bio = ""
        if text_resposta:
            # Agafar primers paràgrafs com a bio
            linies = text_resposta.strip().split("\n")
            bio = " ".join(linies[:3])[:500]

        return InformeInvestigacio(
            autor_nom_complet=autor,
            obra_titol_original=obra,
            autor_bio_breu=bio,
            fiabilitat=3.0,
        )

    def _guardar_a_memoria(
        self,
        informe: InformeInvestigacio,
        memoria: MemoriaContextual,
    ) -> None:
        """Guarda l'informe a la memòria contextual."""
        # Construir bio completa
        autor_bio = informe.autor_nom_complet
        if informe.autor_dates:
            autor_bio += f" ({informe.autor_dates})"
        if informe.autor_origen:
            autor_bio += f", {informe.autor_origen}"
        autor_bio += ". "
        autor_bio += informe.autor_bio_breu

        # Construir context obra
        context_obra = informe.obra_titol_original
        if informe.obra_data_composicio:
            context_obra += f" ({informe.obra_data_composicio})"
        if informe.obra_genere:
            context_obra += f" - {informe.obra_genere}"
        context_obra += ". "
        context_obra += informe.obra_context_creacio

        # Crear ContextInvestigacio
        context = ContextInvestigacio(
            autor_bio=autor_bio,
            context_historic=informe.autor_context_historic,
            context_obra=context_obra,
            influencies=informe.autor_influencies,
            temes_principals=informe.obra_temes_principals,
        )
        memoria.establir_context_investigacio(context)

        # Afegir notes pendents per l'anotador
        for personatge in informe.personatges_mencions:
            memoria.afegir_nota_pendent(f"[H] Personatge històric: {personatge}")
        for referencia in informe.referencies_culturals:
            memoria.afegir_nota_pendent(f"[C] Referència cultural: {referencia}")
        for terme in informe.termes_tecnics:
            memoria.afegir_nota_pendent(f"[T] Terme tècnic: {terme}")

        self.logger.log_info(
            self.agent_name,
            f"Guardat a memòria: {len(informe.personatges_mencions)} personatges, "
            f"{len(informe.referencies_culturals)} referències, "
            f"{len(informe.termes_tecnics)} termes"
        )


# =============================================================================
# FUNCIÓ HELPER
# =============================================================================

def investigar_obra(
    autor: str,
    obra: str,
    llengua: str = "llatí",
    text_mostra: str = "",
    memoria: MemoriaContextual | None = None,
) -> InformeInvestigacio:
    """Funció helper per investigar una obra.

    Ús:
        from agents.investigador import investigar_obra

        informe = investigar_obra("Sèneca", "De Brevitate Vitae", "llatí")
        print(informe.autor_bio_breu)
        print(informe.obra_temes_principals)
    """
    agent = InvestigadorAgent()
    return agent.investigar(autor, obra, llengua, text_mostra, memoria)
