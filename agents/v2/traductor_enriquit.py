"""Traductor Enriquit v2.

Traductor que utilitza el context enriquit de l'AnalitzadorPreTraduccio
per produir traduccions menys literals i més literàries, preservant
la veu de l'autor.

Diferències amb el traductor v1:
- Rep context d'anàlisi prèvia (to, recursos, reptes...)
- Incorpora exemples few-shot de traduccions similars
- Instruccions explícites anti-literalitat
- Genera traducció + justificació de decisions
"""

import json
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from agents.base_agent import AgentConfig, AgentResponse, BaseAgent, extract_json_from_text
from agents.v2.models import (
    AnalisiPreTraduccio,
    ContextTraduccioEnriquit,
)

if TYPE_CHECKING:
    from utils.logger import AgentLogger


class ResultatTraduccio(BaseModel):
    """Resultat d'una traducció enriquida."""

    traduccio: str = Field(..., description="Text traduït")
    decisions_clau: list[str] = Field(
        default_factory=list,
        description="Decisions importants preses durant la traducció"
    )
    termes_preservats: dict[str, str] = Field(
        default_factory=dict,
        description="Termes clau i com s'han traduït"
    )
    recursos_adaptats: list[str] = Field(
        default_factory=list,
        description="Com s'han adaptat els recursos literaris"
    )
    notes_traductor: list[str] = Field(
        default_factory=list,
        description="Notes [N.T.] generades"
    )
    confianca: float = Field(
        ge=0, le=1, default=0.8,
        description="Nivell de confiança en la traducció"
    )
    avisos: list[str] = Field(
        default_factory=list,
        description="Aspectes que poden requerir revisió humana"
    )


class TraductorEnriquit(BaseAgent):
    """Traductor que utilitza context enriquit per a traduccions literàries.

    A diferència del traductor bàsic, aquest agent:
    1. Rep anàlisi prèvia del text (to, recursos, reptes)
    2. Incorpora exemples few-shot de traduccions similars
    3. Segueix instruccions explícites per evitar literalitat
    4. Documenta les decisions preses
    """

    agent_name: str = "TraductorEnriquit"

    def __init__(
        self,
        config: AgentConfig | None = None,
        logger: "AgentLogger | None" = None,
    ) -> None:
        super().__init__(config, logger)

    @property
    def system_prompt(self) -> str:
        return """Ets un traductor literari expert. La teva missió és produir traduccions al català que siguin LITERÀRIAMENT EXCEL·LENTS, no merament correctes.

══════════════════════════════════════════════════════════════════════════════
PRINCIPI FONAMENTAL
══════════════════════════════════════════════════════════════════════════════

NO TRADUEIXIS PARAULES. TRADUEIX SENTIT, TO I VEU.

Una traducció literal és un FRACÀS, encara que sigui "correcta".
El teu objectiu és que el lector català VISQUI l'experiència que viuria
un lector de l'original.

══════════════════════════════════════════════════════════════════════════════
PROCÉS DE TRADUCCIÓ
══════════════════════════════════════════════════════════════════════════════

1. LLEGEIX L'ANÀLISI PRÈVIA (si es proporciona)
   - Comprèn el to i la veu de l'autor
   - Nota els recursos literaris a preservar
   - Anticipa els reptes identificats
   - Segueix les recomanacions

2. ESTUDIA ELS EXEMPLES FEW-SHOT (si es proporcionen)
   - Observa com altres traduccions de qualitat resolen problemes similars
   - Aprèn dels patrons de naturalització
   - Evita els errors que els exemples assenyalen

3. TRADUEIX AMB LLIBERTAT CONTROLADA
   - Prioritza: VEU DE L'AUTOR > FLUÏDESA > LITERALITAT
   - Reordena, reformula, adapta el que calgui
   - Preserva el SENTIT i el TO, no les paraules
   - Usa el glossari si es proporciona (però amb criteri)

4. DOCUMENTA LES DECISIONS IMPORTANTS
   - Per què has triat una opció sobre una altra
   - Com has adaptat recursos literaris
   - Què has hagut de sacrificar i per què

══════════════════════════════════════════════════════════════════════════════
ERRORS A EVITAR (segons llengua origen)
══════════════════════════════════════════════════════════════════════════════

LLATÍ:
✗ Mantenir hipèrbatons artificiosos
✗ Ablatius absoluts literals ("havent estat dit això")
✗ Períodes de 10 línies sense pausa
✓ Reordenar naturalment, trencar si cal, fluir

GREC:
✗ Partícules traduïdes mecànicament (μέν...δέ → "d'una banda...d'altra")
✗ Compostos monstruosos
✓ Traduir FUNCIÓ de partícules, no forma

JAPONÈS:
✗ Ordre SOV residual
✗ Subjectes omesos que creen confusió
✗ Keigo traduït literalment
✗ Onomatopeies sense adaptar
✓ Fluir en SVO, explicitar quan cal, adaptar registre

ANGLÈS:
✗ Gerundis per tot arreu ("estant fent")
✗ Passives innecessàries
✗ Falsos amics (actually ≠ actualment)
✓ Infinitius, actives, vigilar interferències

ALEMANY:
✗ Verbs al final de la frase
✗ Compostos de 15 lletres
✗ Subordinades infinites
✓ Reordenar, descompondre, simplificar

══════════════════════════════════════════════════════════════════════════════
CRITERIS PER GÈNERE
══════════════════════════════════════════════════════════════════════════════

FILOSOFIA:
- Claredat expositiva per sobre de tot
- Precisió terminològica (seguir glossari)
- Permetre frases llargues si són clares
- TO: didàctic, rigorós, accessible

NARRATIVA:
- Preservar la VEU del narrador
- Mantenir ritme narratiu
- Diàlegs naturals i creïbles
- TO: el que l'autor hagi triat

POESIA:
- Sentit > Ritme > Literalitat
- Buscar equivalents sonors si és possible
- Permetre llicències per musicalitat
- TO: el del poema original

TEATRE:
- ORALITAT: ha de sonar bé en veu alta
- Diàlegs àgils, no literaris
- Frases que "es puguin dir"
- TO: viu, dinàmic

ASSAIG:
- Claredat argumentativa
- To personal de l'autor
- Transicions lògiques
- TO: el de l'assagista

══════════════════════════════════════════════════════════════════════════════
FORMAT DE RESPOSTA (JSON ESTRICTE)
══════════════════════════════════════════════════════════════════════════════

{
    "traduccio": "<TEXT TRADUÏT COMPLET>",
    "decisions_clau": [
        "<Decisió 1: per què X en lloc de Y>",
        "<Decisió 2: com s'ha resolt el repte Z>"
    ],
    "termes_preservats": {
        "<terme original>": "<traducció triada i per què>"
    },
    "recursos_adaptats": [
        "<Recurs 1: com s'ha preservat o adaptat>",
        "<Recurs 2: ...>"
    ],
    "notes_traductor": [
        "<[N.T.] que s'han inclòs al text, si n'hi ha>"
    ],
    "confianca": <0.0-1.0>,
    "avisos": [
        "<Aspectes que podrien requerir revisió humana>"
    ]
}

══════════════════════════════════════════════════════════════════════════════
IMPORTANT
══════════════════════════════════════════════════════════════════════════════

- La traducció ha de poder llegir-se SENSE saber que és traducció
- Si dubtes entre literal i natural, tria NATURAL
- Les decisions_clau han de justificar les eleccions no òbvies
- Els avisos són per passatges especialment difícils o ambigus"""

    def traduir(
        self,
        context: ContextTraduccioEnriquit,
    ) -> ResultatTraduccio:
        """Tradueix un text utilitzant el context enriquit.

        Args:
            context: Context complet amb anàlisi, exemples i glossari.

        Returns:
            ResultatTraduccio amb la traducció i metadades.
        """
        prompt = self._construir_prompt(context)
        response = self.process(prompt)

        # Parsejar resposta (robust)
        data = extract_json_from_text(response.content)
        if data and data.get("traduccio"):
            return ResultatTraduccio(
                traduccio=data.get("traduccio", ""),
                decisions_clau=data.get("decisions_clau", []),
                termes_preservats=data.get("termes_preservats", {}),
                recursos_adaptats=data.get("recursos_adaptats", []),
                notes_traductor=data.get("notes_traductor", []),
                confianca=data.get("confianca", 0.8),
                avisos=data.get("avisos", []),
            )

        # Si falla el parsing, intentar extreure la traducció del text
        self.log_warning("No s'ha pogut parsejar JSON, extraient traducció del text")
        return ResultatTraduccio(
            traduccio=self._extreure_traduccio(response.content),
            confianca=0.7,
            avisos=["Resposta no estructurada"],
        )

    def _construir_prompt(self, context: ContextTraduccioEnriquit) -> str:
        """Construeix el prompt complet per a la traducció."""
        seccions = []

        # Capçalera
        seccions.append(f"TRADUEIX el següent text en {context.llengua_origen} al català literari.")

        if context.autor:
            seccions.append(f"\nAutor: {context.autor}")
        if context.obra:
            seccions.append(f"Obra: {context.obra}")
        if context.genere:
            seccions.append(f"Gènere: {context.genere}")

        # Context enriquit (anàlisi + exemples + glossari)
        prompt_context = context.to_prompt_context()
        if prompt_context.strip():
            seccions.append("\n" + "="*60)
            seccions.append("CONTEXT ENRIQUIT (llegeix atentament abans de traduir)")
            seccions.append("="*60)
            seccions.append(prompt_context)

        # Instruccions específiques si hi ha anàlisi
        if context.analisi:
            seccions.append("\n" + "="*60)
            seccions.append("INSTRUCCIONS ESPECÍFIQUES PER AQUEST TEXT")
            seccions.append("="*60)

            if context.analisi.prioritats:
                seccions.append("\nPRIORITATS (en ordre d'importància):")
                for i, p in enumerate(context.analisi.prioritats, 1):
                    seccions.append(f"  {i}. {p}")

            if context.analisi.que_evitar:
                seccions.append("\nEVITA ESPECIALMENT:")
                for e in context.analisi.que_evitar:
                    seccions.append(f"  ✗ {e}")

            if context.analisi.recomanacions_generals:
                seccions.append(f"\nRECOMANACIÓ GENERAL:\n{context.analisi.recomanacions_generals}")

        # Text a traduir
        seccions.append("\n" + "="*60)
        seccions.append(f"TEXT ORIGINAL ({context.llengua_origen.upper()})")
        seccions.append("="*60)
        seccions.append(context.text_original)

        # Instrucció final
        seccions.append("\n" + "="*60)
        seccions.append("Tradueix ara. Recorda: SENTIT i VEU per sobre de literalitat.")
        seccions.append("="*60)

        return "\n".join(seccions)

    def _extreure_traduccio(self, text: str) -> str:
        """Intenta extreure la traducció d'una resposta no estructurada."""
        # Buscar patrons comuns
        import re

        # Buscar bloc de traducció
        patterns = [
            r'"traduccio":\s*"([^"]+)"',
            r'TRADUCCIÓ:?\s*\n(.+?)(?:\n\n|\Z)',
            r'Text traduït:?\s*\n(.+?)(?:\n\n|\Z)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # Si no trobem res, retornar el text sencer (pot ser la traducció directa)
        return text.strip()

    def traduir_simple(
        self,
        text: str,
        llengua_origen: str = "llatí",
        autor: str | None = None,
        obra: str | None = None,
        genere: str = "narrativa",
        glossari: dict[str, str] | None = None,
    ) -> ResultatTraduccio:
        """Mètode de conveniència per traduccions sense anàlisi prèvia.

        Crea un context mínim i tradueix. Per a traduccions de més qualitat,
        usar `traduir()` amb un `ContextTraduccioEnriquit` complet.

        Args:
            text: Text a traduir.
            llengua_origen: Llengua del text original.
            autor: Autor (opcional).
            obra: Obra (opcional).
            genere: Gènere literari.
            glossari: Glossari de termes (opcional).

        Returns:
            ResultatTraduccio amb la traducció.
        """
        context = ContextTraduccioEnriquit(
            text_original=text,
            llengua_origen=llengua_origen,
            autor=autor,
            obra=obra,
            genere=genere,
            glossari=glossari,
        )
        return self.traduir(context)


class TraductorAmbAnalisi:
    """Combina AnalitzadorPreTraduccio i TraductorEnriquit en un sol flux.

    Aquesta classe orquestra el flux complet:
    1. Analitza el text original
    2. Selecciona exemples few-shot
    3. Tradueix amb context enriquit
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        logger: "AgentLogger | None" = None,
        corpus_path: str | None = None,
    ) -> None:
        """Inicialitza el traductor amb anàlisi.

        Args:
            config: Configuració pels agents.
            logger: Logger per al seguiment.
            corpus_path: Ruta al corpus d'exemples few-shot.
        """
        from agents.v2.analitzador_pre import (
            AnalitzadorPreTraduccio,
            SelectorExemplesFewShot,
        )

        self.analitzador = AnalitzadorPreTraduccio(config, logger)
        self.traductor = TraductorEnriquit(config, logger)
        self.selector = SelectorExemplesFewShot(corpus_path)

    def traduir(
        self,
        text: str,
        llengua_origen: str = "llatí",
        autor: str | None = None,
        obra: str | None = None,
        genere: str | None = None,
        glossari: dict[str, str] | None = None,
        max_exemples_fewshot: int = 5,
        saltar_analisi: bool = False,
    ) -> tuple[ResultatTraduccio, AnalisiPreTraduccio | None]:
        """Tradueix un text amb anàlisi prèvia i exemples few-shot.

        Args:
            text: Text a traduir.
            llengua_origen: Llengua del text original.
            autor: Autor (opcional).
            obra: Obra (opcional).
            genere: Gènere literari (si no s'especifica, es detecta).
            glossari: Glossari de termes (opcional).
            max_exemples_fewshot: Màxim d'exemples a usar.
            saltar_analisi: Si True, no fa anàlisi prèvia (més ràpid).

        Returns:
            Tupla amb (ResultatTraduccio, AnalisiPreTraduccio o None).
        """
        analisi = None

        # Fase 1: Anàlisi (si no es salta)
        if not saltar_analisi:
            analisi = self.analitzador.analitzar(
                text=text,
                llengua_origen=llengua_origen,
                autor=autor,
                obra=obra,
                genere=genere,
            )
            # Usar gènere detectat si no s'ha especificat
            if genere is None:
                genere = analisi.genere_detectat

        genere = genere or "narrativa"

        # Fase 2: Seleccionar exemples few-shot
        exemples = self.selector.seleccionar(
            llengua_origen=llengua_origen,
            genere=genere,
            autor=autor,
            max_exemples=max_exemples_fewshot,
        )

        # Fase 3: Crear context enriquit
        context = ContextTraduccioEnriquit(
            text_original=text,
            llengua_origen=llengua_origen,
            autor=autor,
            obra=obra,
            genere=genere,
            analisi=analisi,
            exemples_fewshot=exemples,
            glossari=glossari,
        )

        # Fase 4: Traduir
        resultat = self.traductor.traduir(context)

        return resultat, analisi

    def traduir_rapid(
        self,
        text: str,
        llengua_origen: str = "llatí",
        genere: str = "narrativa",
    ) -> str:
        """Traducció ràpida sense anàlisi ni exemples.

        Per a traduccions ràpides on la qualitat màxima no és crítica.

        Args:
            text: Text a traduir.
            llengua_origen: Llengua del text.
            genere: Gènere literari.

        Returns:
            Text traduït (només el text, sense metadades).
        """
        resultat = self.traductor.traduir_simple(
            text=text,
            llengua_origen=llengua_origen,
            genere=genere,
        )
        return resultat.traduccio
