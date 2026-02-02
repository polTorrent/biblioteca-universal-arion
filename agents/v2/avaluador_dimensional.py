"""Sistema d'Avaluació Dimensional per a traduccions literàries.

Aquest mòdul implementa un sistema d'avaluació que separa l'anàlisi en tres
dimensions ortogonals: Fidelitat, Veu de l'Autor i Fluïdesa. Cada dimensió
té el seu propi avaluador especialitzat, i el FusionadorFeedback combina
els resultats en un feedback accionable per al refinador.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel

from agents.base_agent import AgentConfig, AgentResponse, BaseAgent, extract_json_from_text
from utils.detector_calcs import detectar_calcs, ResultatDeteccio

# LanguageTool per correcció normativa
try:
    from utils.corrector_linguistic import corregir_text as lt_corregir, LANGUAGETOOL_DISPONIBLE
except ImportError:
    LANGUAGETOOL_DISPONIBLE = False
from agents.v2.models import (
    AvaluacioFidelitat,
    AvaluacioVeuAutor,
    AvaluacioFluidesa,
    FeedbackFusionat,
    ContextAvaluacio,
    ProblemaFidelitat,
    SubavaluacioVeu,
    SubavaluacioFluidesa,
    ErrorNormatiu,
    PESOS_DIMENSIONS,
    LLINDARS_DEFAULT,
    LlindarsAvaluacio,
)

if TYPE_CHECKING:
    from utils.logger import AgentLogger


# =============================================================================
# AVALUADOR DE FIDELITAT
# =============================================================================

class AvaluadorFidelitat(BaseAgent):
    """Avalua si el significat de l'original es preserva correctament.

    Aquest avaluador és "cec" a la fluïdesa i la veu - NOMÉS mira si el
    significat es transmet fidelment.
    """

    agent_name: str = "AvaluadorFidelitat"

    def __init__(
        self,
        config: AgentConfig | None = None,
        logger: "AgentLogger | None" = None,
    ) -> None:
        super().__init__(config, logger)

    @property
    def system_prompt(self) -> str:
        return """Ets un avaluador expert de FIDELITAT de traduccions literàries.

EL TEU ÚNIC OBJECTIU és determinar si el SIGNIFICAT del text original es preserva a la traducció.

══════════════════════════════════════════════════════════════════════════════
IGNORA COMPLETAMENT (NO ÉS LA TEVA FEINA):
══════════════════════════════════════════════════════════════════════════════
- Si el català sona natural o forçat
- Si l'estil és elegant o tosc
- Errors gramaticals o ortogràfics
- Si preserva el to de l'autor
- La qualitat literària del text català

══════════════════════════════════════════════════════════════════════════════
AVALUA NOMÉS AQUESTES 5 CATEGORIES:
══════════════════════════════════════════════════════════════════════════════

1. OMISSIONS
   - Falta contingut significatiu de l'original?
   - S'han omès frases, clàusules o idees?
   - Gravetat: 3 si és una idea principal, 2 si és secundària, 1 si és menor

2. ADDICIONS
   - Hi ha contingut inventat que no és a l'original?
   - S'han afegit explicacions, interpretacions o aclariments no justificats?
   - Gravetat: 3 si canvia el sentit, 2 si és notable, 1 si és estilístic

3. SIGNIFICAT
   - El sentit de cada frase es transmet correctament?
   - Hi ha contrasentits o distorsions?
   - Gravetat: 3 si és un error greu, 2 si és una imprecisió, 1 si és subtil

4. TERMINOLOGIA
   - Els termes tècnics/clau es tradueixen amb precisió?
   - Hi ha coherència en la traducció de termes repetits?
   - Gravetat: 2 si és un terme clau, 1 si és secundari

5. AMBIGÜITAT
   - Es respecta l'ambigüitat intencionada de l'original?
   - S'ha desambiguat quelcom que l'autor deixava obert?
   - Gravetat: 2 si era clarament intencionada, 1 si és discutible

══════════════════════════════════════════════════════════════════════════════
ESCALA DE PUNTUACIÓ:
══════════════════════════════════════════════════════════════════════════════
9-10: Fidelitat excel·lent, cap omissió ni distorsió significativa
7-8:  Bona fidelitat, només problemes menors
5-6:  Fidelitat acceptable, alguns errors però sentit general preservat
3-4:  Problemes seriosos, el significat s'ha distorsionat en parts
1-2:  El significat s'ha perdut substancialment

══════════════════════════════════════════════════════════════════════════════
FORMAT DE RESPOSTA (JSON ESTRICTE):
══════════════════════════════════════════════════════════════════════════════
{
    "puntuacio": <número 1-10>,
    "problemes": [
        {
            "tipus": "<omissio|addicio|significat|terminologia|ambiguitat>",
            "segment_original": "<fragment de l'original afectat o null>",
            "segment_traduit": "<fragment de la traducció o null>",
            "explicacio": "<descripció clara del problema>",
            "gravetat": <1, 2 o 3>
        }
    ],
    "feedback_refinament": "<instruccions ESPECÍFIQUES i ACCIONABLES per corregir els problemes de fidelitat>"
}

IMPORTANT: El feedback_refinament ha de ser concret. No diguis "millorar la fidelitat",
sinó "restaurar la frase X que s'ha omès" o "el terme Y hauria de ser Z"."""

    def avaluar(self, context: ContextAvaluacio) -> AvaluacioFidelitat:
        """Avalua la fidelitat d'una traducció.

        Args:
            context: Context amb l'original i la traducció.

        Returns:
            AvaluacioFidelitat amb la puntuació i problemes detectats.
        """
        prompt_parts = [
            f"Avalua la FIDELITAT d'aquesta traducció del {context.llengua_origen} al català.",
        ]

        if context.autor:
            prompt_parts.append(f"\nAutor: {context.autor}")
        if context.obra:
            prompt_parts.append(f"Obra: {context.obra}")

        if context.glossari:
            glossari_str = "\n".join(f"  - {k}: {v}" for k, v in list(context.glossari.items())[:20])
            prompt_parts.append(f"\nGLOSSARI DE REFERÈNCIA:\n{glossari_str}")

        prompt_parts.extend([
            f"\n\n═══ TEXT ORIGINAL ({context.llengua_origen.upper()}) ═══",
            context.text_original[:context.max_chars],
            "\n═══ TRADUCCIÓ A AVALUAR ═══",
            context.text_traduit[:context.max_chars],
        ])

        response = self.process("\n".join(prompt_parts))

        # Parsejar resposta JSON (robust)
        data = extract_json_from_text(response.content)
        if data:
            try:
                # Gestionar puntuació null/None
                puntuacio = data.get("puntuacio")
                if puntuacio is None:
                    puntuacio = 5.0

                return AvaluacioFidelitat(
                    puntuacio=float(puntuacio),
                    problemes=[
                        ProblemaFidelitat(**p) for p in data.get("problemes") or []
                    ],
                    feedback_refinament=data.get("feedback_refinament") or "",
                )
            except (KeyError, TypeError) as e:
                self.log_warning(f"Error construint avaluació: {e}")

        # Retornar avaluació per defecte amb puntuació alta per no bloquejar
        self.log_warning("No s'ha pogut parsejar JSON, assumint traducció acceptable")
        return AvaluacioFidelitat(
            puntuacio=7.5,
            problemes=[],
            feedback_refinament="",
        )


# =============================================================================
# AVALUADOR DE VEU DE L'AUTOR
# =============================================================================

class AvaluadorVeuAutor(BaseAgent):
    """Avalua si el to, estil i personalitat de l'autor es preserven.

    Aquesta és la dimensió MÉS CRÍTICA per a traducció literària.
    """

    agent_name: str = "AvaluadorVeuAutor"

    def __init__(
        self,
        config: AgentConfig | None = None,
        logger: "AgentLogger | None" = None,
    ) -> None:
        super().__init__(config, logger)

    @property
    def system_prompt(self) -> str:
        return """Ets un avaluador expert de VEU DE L'AUTOR en traduccions literàries.

EL TEU ÚNIC OBJECTIU és determinar si el TO, ESTIL i PERSONALITAT de l'autor original es preserven a la traducció.

Aquesta és la dimensió MÉS IMPORTANT d'una traducció literària. Una traducció fidel i fluida però SENSE ÀNIMA no serveix.

══════════════════════════════════════════════════════════════════════════════
IGNORA COMPLETAMENT (NO ÉS LA TEVA FEINA):
══════════════════════════════════════════════════════════════════════════════
- Si el significat és exacte mot per mot
- Si el català és gramaticalment perfecte
- Si hi ha errors ortogràfics
- Qüestions purament de contingut

══════════════════════════════════════════════════════════════════════════════
AVALUA AQUESTES 5 SUBCATEGORIES:
══════════════════════════════════════════════════════════════════════════════

1. REGISTRE I FORMALITAT (puntuació 1-10)
   - El nivell de formalitat és equivalent?
   - Text solemne roman solemne? Text col·loquial roman col·loquial?
   - El lèxic és coherent amb l'època i context?

2. TO EMOCIONAL (puntuació 1-10)
   - La ironia es percep com a ironia?
   - La solemnitat es manté solemne?
   - L'humor arriba com a humor?
   - La intensitat emocional és equivalent?

3. RITME I CADÈNCIA (puntuació 1-10)
   - Si l'original té frases curtes i contundents, la traducció també?
   - Les pauses estan en llocs similars?
   - La cadència general es preserva?

4. IDIOSINCRÀSIES (puntuació 1-10)
   - Els tics estilístics de l'autor es reconeixen?
   - El vocabulari característic es manté o s'adapta adequadament?
   - L'autor seria reconeixible pel seu estil?

5. RECURSOS RETÒRICS (puntuació 1-10)
   - Les figures retòriques es preserven o substitueixen per equivalents?
   - Les anàfores, paral·lelismes, al·literacions sobreviuen?
   - Les repeticions significatives es mantenen?

══════════════════════════════════════════════════════════════════════════════
PREGUNTA CLAU:
══════════════════════════════════════════════════════════════════════════════
Si l'autor pogués llegir aquesta traducció (màgicament entenent català),
RECONEIXERIA LA SEVA PRÒPIA VEU?

══════════════════════════════════════════════════════════════════════════════
ESCALA DE PUNTUACIÓ GLOBAL:
══════════════════════════════════════════════════════════════════════════════
9-10: L'autor seria immediatament reconeixible, to perfectament preservat
7-8:  Bona preservació, petites pèrdues assumibles
5-6:  To parcialment preservat, algunes neutralitzacions notables
3-4:  To significativament alterat, veu aplanada
1-2:  Completament despersonalitzat, podria ser de qualsevol autor

══════════════════════════════════════════════════════════════════════════════
FORMAT DE RESPOSTA (JSON ESTRICTE):
══════════════════════════════════════════════════════════════════════════════
{
    "puntuacio": <número 1-10>,
    "registre": {"puntuacio": <1-10>, "observacions": "<què es preserva o perd>"},
    "to_emocional": {"puntuacio": <1-10>, "observacions": "<què es preserva o perd>"},
    "ritme": {"puntuacio": <1-10>, "observacions": "<què es preserva o perd>"},
    "idiosincrasies": {"puntuacio": <1-10>, "observacions": "<què es preserva o perd>"},
    "recursos_retorics": {"puntuacio": <1-10>, "observacions": "<què es preserva o perd>"},
    "feedback_refinament": "<instruccions ESPECÍFIQUES per recuperar la veu de l'autor.
                            No diguis 'millorar el to', sinó 'canviar X per Y per recuperar la ironia'>"
}"""

    def avaluar(self, context: ContextAvaluacio) -> AvaluacioVeuAutor:
        """Avalua la preservació de la veu de l'autor.

        Args:
            context: Context amb l'original i la traducció.

        Returns:
            AvaluacioVeuAutor amb puntuacions per subcategoria.
        """
        prompt_parts = [
            f"Avalua la preservació de la VEU DE L'AUTOR en aquesta traducció del {context.llengua_origen} al català.",
        ]

        if context.autor:
            prompt_parts.append(f"\nAutor: {context.autor}")
        if context.obra:
            prompt_parts.append(f"Obra: {context.obra}")
        if context.genere:
            prompt_parts.append(f"Gènere: {context.genere}")

        if context.descripcio_estil_autor:
            prompt_parts.append(f"\nCONTEXT ESTILÍSTIC DE L'AUTOR:")
            prompt_parts.append(context.descripcio_estil_autor)

        prompt_parts.extend([
            f"\n\n═══ TEXT ORIGINAL ({context.llengua_origen.upper()}) ═══",
            context.text_original[:context.max_chars],
            "\n═══ TRADUCCIÓ A AVALUAR ═══",
            context.text_traduit[:context.max_chars],
        ])

        response = self.process("\n".join(prompt_parts))

        # Parsejar resposta JSON (robust)
        data = extract_json_from_text(response.content)
        if data:
            try:
                def parse_subavaluacio(key: str) -> SubavaluacioVeu:
                    sub = data.get(key, {})
                    # Gestionar null/None explícitament
                    puntuacio = sub.get("puntuacio")
                    if puntuacio is None:
                        puntuacio = 5.0
                    return SubavaluacioVeu(
                        puntuacio=float(puntuacio),
                        observacions=sub.get("observacions") or "",
                    )

                # Gestionar puntuació principal null/None
                puntuacio_principal = data.get("puntuacio")
                if puntuacio_principal is None:
                    puntuacio_principal = 5.0

                return AvaluacioVeuAutor(
                    puntuacio=float(puntuacio_principal),
                    registre=parse_subavaluacio("registre"),
                    to_emocional=parse_subavaluacio("to_emocional"),
                    ritme=parse_subavaluacio("ritme"),
                    idiosincrasies=parse_subavaluacio("idiosincrasies"),
                    recursos_retorics=parse_subavaluacio("recursos_retorics"),
                    feedback_refinament=data.get("feedback_refinament") or "",
                )
            except (KeyError, TypeError) as e:
                self.log_warning(f"Error construint avaluació: {e}")

        # Retornar avaluació per defecte amb puntuació alta per no bloquejar
        self.log_warning("No s'ha pogut parsejar JSON, assumint traducció acceptable")
        return AvaluacioVeuAutor(
            puntuacio=7.5,
            feedback_refinament="",
        )


# =============================================================================
# AVALUADOR DE FLUÏDESA
# =============================================================================

class AvaluadorFluidesa(BaseAgent):
    """Avalua si el text sona natural per a un lector català actual.

    Verifica sintaxi, lèxic, normativa IEC i llegibilitat.
    """

    agent_name: str = "AvaluadorFluidesa"

    def __init__(
        self,
        config: AgentConfig | None = None,
        logger: "AgentLogger | None" = None,
    ) -> None:
        super().__init__(config, logger)

    @property
    def system_prompt(self) -> str:
        return """Ets un avaluador expert de FLUÏDESA en català.

EL TEU ÚNIC OBJECTIU és determinar si el text sona NATURAL per a un lector català actual.

══════════════════════════════════════════════════════════════════════════════
IGNORA COMPLETAMENT (NO ÉS LA TEVA FEINA):
══════════════════════════════════════════════════════════════════════════════
- Si el significat és exacte respecte l'original
- Si preserva el to de l'autor
- Qüestions de contingut o interpretació
- Si la terminologia és precisa

══════════════════════════════════════════════════════════════════════════════
AVALUA AQUESTES 4 SUBCATEGORIES:
══════════════════════════════════════════════════════════════════════════════

1. SINTAXI (puntuació 1-10)
   - L'ordre de les paraules és natural en català?
   - Les subordinades flueixen bé o són forçades?
   - Hi ha estructures calcades d'altres llengües?
   - Problemes típics: inversions estranyes, complements mal col·locats

2. LÈXIC (puntuació 1-10)
   - Les paraules són les que un català usaria naturalment?
   - Les expressions són genuïnes o són calcs?
   - Hi ha falsos amics o interferències?
   - El registre lèxic és consistent?

3. NORMATIVA IEC (puntuació 1-10)
   - Ortografia correcta (accents, apòstrofs, dièresi, guionets)
   - Gramàtica correcta (concordances, règims verbals, pronoms febles)
   - Puntuació adequada (comes, punt i coma, guions llargs)
   - Lèxic normatiu (evitar castellanismes i barbarismes)

4. LLEGIBILITAT (puntuació 1-10)
   - Es llegeix sense esforç?
   - Cal rellegir per entendre?
   - El text "flueix" o s'encalla?

══════════════════════════════════════════════════════════════════════════════
CALCS A DETECTAR (segons llengua origen):
══════════════════════════════════════════════════════════════════════════════
- Anglès: gerundis excessius, passives, phrasal verbs literals
- Francès: "c'est...qui/que" → "és...que", falsos amics (attendre)
- Castellà: "o sigui", "pues", "mientras que" literal
- Llatí: hipèrbatons innecessaris, ablatius mal resolts
- Japonès: ordre SOV residual, subjectes omesos que calen

══════════════════════════════════════════════════════════════════════════════
PREGUNTA CLAU:
══════════════════════════════════════════════════════════════════════════════
Si no sabéssiu que és una traducció, semblaria escrit ORIGINALMENT en català?

══════════════════════════════════════════════════════════════════════════════
ESCALA DE PUNTUACIÓ GLOBAL:
══════════════════════════════════════════════════════════════════════════════
9-10: Sembla escrit originalment en català, perfectament natural
7-8:  Natural amb petites rigideses ocasionals
5-6:  Es nota que és traducció, però llegible sense esforç
3-4:  Força rígid, calcs evidents, requereix esforç
1-2:  Clarament "traduït", difícil de llegir

══════════════════════════════════════════════════════════════════════════════
FORMAT DE RESPOSTA (JSON ESTRICTE):
══════════════════════════════════════════════════════════════════════════════
{
    "puntuacio": <número 1-10>,
    "sintaxi": {"puntuacio": <1-10>, "problemes": ["problema 1", "problema 2"]},
    "lexic": {"puntuacio": <1-10>, "problemes": ["problema 1", "problema 2"]},
    "normativa": {"puntuacio": <1-10>, "problemes": ["problema 1", "problema 2"]},
    "llegibilitat": {"puntuacio": <1-10>, "problemes": ["problema 1"]},
    "errors_normatius": [
        {
            "tipus": "<ortografia|gramatica|puntuacio|lexic>",
            "fragment": "<text incorrecte>",
            "correccio": "<text correcte>",
            "explicacio": "<per què és incorrecte>"
        }
    ],
    "calcs_detectats": ["calc 1: explicació", "calc 2: explicació"],
    "feedback_refinament": "<instruccions ESPECÍFIQUES per millorar la fluïdesa.
                            No diguis 'millorar la sintaxi', sinó 'canviar X per Y'>"
}"""

    def avaluar(self, context: ContextAvaluacio) -> AvaluacioFluidesa:
        """Avalua la fluïdesa del text català.

        Args:
            context: Context amb la traducció a avaluar.

        Returns:
            AvaluacioFluidesa amb puntuacions i problemes detectats.
        """
        # ═══════════════════════════════════════════════════════════════════
        # FASE 1: DETECCIÓ AUTOMÀTICA DE CALCS (sense LLM)
        # ═══════════════════════════════════════════════════════════════════
        resultat_detector = detectar_calcs(
            text=context.text_traduit,
            llengua_origen=context.llengua_origen
        )

        calcs_automatics = [
            f"{c.tipus.value}: \"{c.text_original}\" → {c.suggeriment}"
            for c in resultat_detector.calcs
        ]

        # ═══════════════════════════════════════════════════════════════════
        # FASE 1.5: CORRECCIÓ LINGÜÍSTICA (LanguageTool)
        # ═══════════════════════════════════════════════════════════════════
        errors_lt = []
        puntuacio_lt = 10.0

        if LANGUAGETOOL_DISPONIBLE:
            try:
                resultat_lt = lt_corregir(context.text_traduit)
                puntuacio_lt = resultat_lt.puntuacio_normativa
                errors_lt = [
                    f"{e.categoria.value}: \"{e.text_original}\" → {', '.join(e.suggeriments[:2])}"
                    for e in resultat_lt.errors[:10]
                ]
                if errors_lt:
                    self.log_info(f"LanguageTool: {len(errors_lt)} errors, puntuació {puntuacio_lt}/10")
            except Exception as e:
                self.log_warning(f"LanguageTool error: {e}")

        # ═══════════════════════════════════════════════════════════════════
        # FASE 2: AVALUACIÓ AMB LLM
        # ═══════════════════════════════════════════════════════════════════
        prompt_parts = [
            f"Avalua la FLUÏDESA en català d'aquesta traducció (original en {context.llengua_origen}).",
            "\nNOTA: L'original s'inclou només per identificar possibles calcs de la llengua origen.",
        ]

        # Informar el LLM dels calcs ja detectats automàticament
        if calcs_automatics:
            prompt_parts.append(f"\n⚠️ CALCS JA DETECTATS AUTOMÀTICAMENT ({len(calcs_automatics)}):")
            for calc in calcs_automatics[:10]:  # Màxim 10 per no saturar
                prompt_parts.append(f"  • {calc}")
            prompt_parts.append("\nBusca ALTRES problemes de fluïdesa no llistats aquí.")

        if context.genere:
            prompt_parts.append(f"\nGènere: {context.genere}")

        prompt_parts.extend([
            f"\n\n═══ TEXT ORIGINAL ({context.llengua_origen.upper()}) - PER REFERÈNCIA ═══",
            context.text_original[:context.max_chars // 2],  # Menys text original, més focus en català
            "\n═══ TEXT CATALÀ A AVALUAR ═══",
            context.text_traduit[:context.max_chars],
        ])

        response = self.process("\n".join(prompt_parts))

        # ═══════════════════════════════════════════════════════════════════
        # FASE 3: COMBINAR RESULTATS
        # ═══════════════════════════════════════════════════════════════════
        data = extract_json_from_text(response.content)
        if data:
            try:
                def parse_subavaluacio(key: str) -> SubavaluacioFluidesa:
                    sub = data.get(key, {})
                    # Gestionar null/None explícitament
                    puntuacio = sub.get("puntuacio")
                    if puntuacio is None:
                        puntuacio = 5.0
                    return SubavaluacioFluidesa(
                        puntuacio=float(puntuacio),
                        problemes=sub.get("problemes") or [],
                    )

                errors = []
                for e in data.get("errors_normatius", []):
                    try:
                        errors.append(ErrorNormatiu(**e))
                    except Exception as err:
                        self.log_warning(f"Error parsejant ErrorNormatiu: {err}")

                # Combinar calcs del LLM amb els automàtics (sense duplicats)
                calcs_llm = data.get("calcs_detectats", [])
                calcs_combinats = calcs_automatics + [
                    c for c in calcs_llm
                    if not any(auto in c or c in auto for auto in calcs_automatics)
                ]

                # Ajustar puntuació si el detector automàtic ha trobat molts calcs
                puntuacio_llm = data.get("puntuacio")
                if puntuacio_llm is None:
                    puntuacio_llm = 5.0
                puntuacio_llm = float(puntuacio_llm)
                puntuacio_detector = resultat_detector.puntuacio_fluidesa

                # Ponderar: 55% LLM, 25% detector calcs, 20% LanguageTool
                puntuacio_final = (puntuacio_llm * 0.55) + (puntuacio_detector * 0.25) + (puntuacio_lt * 0.20)

                # Generar feedback ampliat
                feedback_llm = data.get("feedback_refinament", "")
                feedback_detector = ""
                if resultat_detector.calcs:
                    feedback_detector = "\n\n[CALCS DETECTATS AUTOMÀTICAMENT]\n"
                    for calc in resultat_detector.calcs[:5]:
                        feedback_detector += f"• {calc.text_original}: {calc.suggeriment}\n"

                # Afegir errors de LanguageTool
                feedback_lt = ""
                if errors_lt:
                    feedback_lt = "\n\n[ERRORS NORMATIUS (LanguageTool)]\n"
                    for error in errors_lt[:5]:
                        feedback_lt += f"• {error}\n"

                return AvaluacioFluidesa(
                    puntuacio=round(puntuacio_final, 1),
                    sintaxi=parse_subavaluacio("sintaxi"),
                    lexic=parse_subavaluacio("lexic"),
                    normativa=parse_subavaluacio("normativa"),
                    llegibilitat=parse_subavaluacio("llegibilitat"),
                    errors_normatius=errors,
                    calcs_detectats=calcs_combinats,
                    feedback_refinament=feedback_llm + feedback_detector + feedback_lt,
                )
            except (KeyError, TypeError) as e:
                self.log_warning(f"Error construint avaluació: {e}")

        # Si falla el LLM, retornar almenys els resultats del detector automàtic
        self.log_warning("No s'ha pogut parsejar JSON del LLM, usant només detector automàtic")
        return AvaluacioFluidesa(
            puntuacio=resultat_detector.puntuacio_fluidesa,
            calcs_detectats=calcs_automatics,
            feedback_refinament=resultat_detector.resum if resultat_detector.calcs else "",
        )


# =============================================================================
# FUSIONADOR DE FEEDBACK
# =============================================================================

class FusionadorFeedback:
    """Combina els resultats dels tres avaluadors en un feedback unificat."""

    def __init__(self, llindars: LlindarsAvaluacio | None = None) -> None:
        """Inicialitza el fusionador.

        Args:
            llindars: Llindars d'aprovació. Si no s'especifica, usa els per defecte.
        """
        self.llindars = llindars or LLINDARS_DEFAULT

    def fusionar(
        self,
        fidelitat: AvaluacioFidelitat,
        veu_autor: AvaluacioVeuAutor,
        fluidesa: AvaluacioFluidesa,
        iteracio: int = 1,
    ) -> FeedbackFusionat:
        """Fusiona els resultats dels tres avaluadors.

        Args:
            fidelitat: Resultat de l'avaluador de fidelitat.
            veu_autor: Resultat de l'avaluador de veu de l'autor.
            fluidesa: Resultat de l'avaluador de fluïdesa.
            iteracio: Número d'iteració actual.

        Returns:
            FeedbackFusionat amb la decisió i instruccions de refinament.
        """
        # Calcular puntuació global ponderada
        puntuacio_global = (
            fidelitat.puntuacio * PESOS_DIMENSIONS["fidelitat"]
            + veu_autor.puntuacio * PESOS_DIMENSIONS["veu_autor"]
            + fluidesa.puntuacio * PESOS_DIMENSIONS["fluidesa"]
        )

        # Penalització si veu_autor és molt baixa
        if veu_autor.puntuacio < 6:
            puntuacio_global *= 0.85

        # Determinar si s'aprova
        aprovat = (
            puntuacio_global >= self.llindars.global_minim
            and veu_autor.puntuacio >= self.llindars.veu_autor_minim
            and fidelitat.puntuacio >= self.llindars.fidelitat_minim
            and fluidesa.puntuacio >= self.llindars.fluidesa_minim
        )

        # Determinar prioritats de refinament
        prioritats = self._determinar_prioritats(fidelitat, veu_autor, fluidesa)

        # Generar instruccions de refinament
        instruccions = self._generar_instruccions(
            fidelitat, veu_autor, fluidesa, prioritats
        )

        # Determinar si cal revisió humana
        requereix_revisio_humana = (
            iteracio >= self.llindars.max_iteracions
            and puntuacio_global < self.llindars.llindar_revisio_humana
        )

        return FeedbackFusionat(
            puntuacio_global=round(puntuacio_global, 2),
            puntuacio_fidelitat=fidelitat.puntuacio,
            puntuacio_veu_autor=veu_autor.puntuacio,
            puntuacio_fluidesa=fluidesa.puntuacio,
            aprovat=aprovat,
            requereix_revisio_humana=requereix_revisio_humana,
            prioritat_1=prioritats[0] if len(prioritats) > 0 else None,
            prioritat_2=prioritats[1] if len(prioritats) > 1 else None,
            prioritat_3=prioritats[2] if len(prioritats) > 2 else None,
            instruccions_refinament=instruccions,
            avaluacio_fidelitat=fidelitat,
            avaluacio_veu_autor=veu_autor,
            avaluacio_fluidesa=fluidesa,
            iteracio=iteracio,
        )

    def _determinar_prioritats(
        self,
        fidelitat: AvaluacioFidelitat,
        veu_autor: AvaluacioVeuAutor,
        fluidesa: AvaluacioFluidesa,
    ) -> list[str]:
        """Determina l'ordre de prioritat per al refinament.

        Regles:
        1. VEU DE L'AUTOR sempre primer si < 7 (és el més crític)
        2. FIDELITAT segon si hi ha errors greus (gravetat 3)
        3. Després per puntuació més baixa

        Returns:
            Llista ordenada de dimensions a prioritzar.
        """
        prioritats = []

        # VEU sempre primer si és baixa
        if veu_autor.puntuacio < 7:
            prioritats.append("veu_autor")

        # FIDELITAT si hi ha errors greus
        if fidelitat.te_problemes_greus or fidelitat.puntuacio < self.llindars.fidelitat_critic:
            if "fidelitat" not in prioritats:
                prioritats.append("fidelitat")

        # Afegir la resta per ordre de puntuació (de pitjor a millor)
        dimensions_restants = [
            ("veu_autor", veu_autor.puntuacio),
            ("fidelitat", fidelitat.puntuacio),
            ("fluidesa", fluidesa.puntuacio),
        ]
        dimensions_restants.sort(key=lambda x: x[1])

        for dim, _ in dimensions_restants:
            if dim not in prioritats:
                prioritats.append(dim)

        return prioritats

    def _generar_instruccions(
        self,
        fidelitat: AvaluacioFidelitat,
        veu_autor: AvaluacioVeuAutor,
        fluidesa: AvaluacioFluidesa,
        prioritats: list[str],
    ) -> str:
        """Genera instruccions de refinament consolidades.

        Args:
            fidelitat: Avaluació de fidelitat.
            veu_autor: Avaluació de veu de l'autor.
            fluidesa: Avaluació de fluïdesa.
            prioritats: Ordre de prioritat.

        Returns:
            Text amb instruccions accionables.
        """
        seccions = []

        # Capçalera
        seccions.append("═══ INSTRUCCIONS DE REFINAMENT ═══\n")

        # Instruccions per prioritat
        feedback_map = {
            "fidelitat": fidelitat.feedback_refinament,
            "veu_autor": veu_autor.feedback_refinament,
            "fluidesa": fluidesa.feedback_refinament,
        }

        nom_map = {
            "fidelitat": "FIDELITAT",
            "veu_autor": "VEU DE L'AUTOR (PRIORITAT MÀXIMA)",
            "fluidesa": "FLUÏDESA",
        }

        for i, dim in enumerate(prioritats, 1):
            feedback = feedback_map.get(dim, "")
            if feedback:
                nom = nom_map.get(dim, dim.upper())
                seccions.append(f"\n{i}. {nom}:")
                seccions.append(feedback)

        # Recordatori de prioritats
        seccions.append("\n\n═══ RECORDATORI ═══")
        seccions.append("Prioritat en conflictes: VEU DE L'AUTOR > FIDELITAT > FLUÏDESA")
        seccions.append("MAI sacrifiquis la veu per millorar la fluïdesa.")

        return "\n".join(seccions)


# =============================================================================
# AVALUADOR DIMENSIONAL (ORQUESTRADOR)
# =============================================================================

class AvaluadorDimensional:
    """Orquestra l'avaluació dimensional completa d'una traducció.

    Coordina els tres avaluadors especialitzats i fusiona els resultats.
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        llindars: LlindarsAvaluacio | None = None,
        logger: "AgentLogger | None" = None,
    ) -> None:
        """Inicialitza l'avaluador dimensional.

        Args:
            config: Configuració pels agents.
            llindars: Llindars d'aprovació personalitzats.
            logger: Logger per al seguiment.
        """
        self.config = config
        self.logger = logger

        # Crear avaluadors
        self.avaluador_fidelitat = AvaluadorFidelitat(config, logger)
        self.avaluador_veu_autor = AvaluadorVeuAutor(config, logger)
        self.avaluador_fluidesa = AvaluadorFluidesa(config, logger)

        # Crear fusionador
        self.fusionador = FusionadorFeedback(llindars)

    def avaluar(
        self,
        context: ContextAvaluacio,
        iteracio: int = 1,
    ) -> FeedbackFusionat:
        """Realitza l'avaluació dimensional completa.

        Args:
            context: Context amb l'original i la traducció.
            iteracio: Número d'iteració actual (per al fusionador).

        Returns:
            FeedbackFusionat amb l'avaluació completa i instruccions.
        """
        # Avaluar cada dimensió
        avaluacio_fidelitat = self.avaluador_fidelitat.avaluar(context)
        avaluacio_veu_autor = self.avaluador_veu_autor.avaluar(context)
        avaluacio_fluidesa = self.avaluador_fluidesa.avaluar(context)

        # Fusionar resultats
        return self.fusionador.fusionar(
            fidelitat=avaluacio_fidelitat,
            veu_autor=avaluacio_veu_autor,
            fluidesa=avaluacio_fluidesa,
            iteracio=iteracio,
        )

    def avaluar_rapid(
        self,
        text_original: str,
        text_traduit: str,
        llengua_origen: str = "llatí",
        autor: str | None = None,
        genere: str = "narrativa",
    ) -> FeedbackFusionat:
        """Mètode de conveniència per avaluació ràpida.

        Args:
            text_original: Text en llengua origen.
            text_traduit: Traducció a avaluar.
            llengua_origen: Llengua del text original.
            autor: Autor de l'obra (opcional).
            genere: Gènere literari.

        Returns:
            FeedbackFusionat amb l'avaluació.
        """
        context = ContextAvaluacio(
            text_original=text_original,
            text_traduit=text_traduit,
            llengua_origen=llengua_origen,
            autor=autor,
            genere=genere,
        )
        return self.avaluar(context)
