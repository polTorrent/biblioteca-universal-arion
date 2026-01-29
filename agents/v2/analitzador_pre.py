"""Agent Analitzador Pre-Traducció.

Analitza el text original ABANS de traduir per identificar:
- Paraules clau i termes crítics
- To i veu de l'autor
- Recursos literaris
- Reptes de traducció anticipats
- Recomanacions per evitar literalitat

Aquest context enriquit millora significativament la qualitat de la traducció.
"""

import json
from typing import TYPE_CHECKING

from agents.base_agent import AgentConfig, AgentResponse, BaseAgent, extract_json_from_text
from agents.v2.models import (
    AnalisiPreTraduccio,
    ParaulaClau,
    RecursLiterari,
    RepteTraduccio,
    ContextTraduccioEnriquit,
)

if TYPE_CHECKING:
    from utils.logger import AgentLogger


class AnalitzadorPreTraduccio(BaseAgent):
    """Analitza el text original per preparar una traducció de qualitat.

    Segons la recerca (MAPS - Multi-Aspect Prompting), analitzar el text
    ABANS de traduir millora significativament la qualitat, reduint la
    literalitat i preservant millor la veu de l'autor.
    """

    agent_name: str = "AnalitzadorPre"

    def __init__(
        self,
        config: AgentConfig | None = None,
        logger: "AgentLogger | None" = None,
    ) -> None:
        super().__init__(config, logger)

    @property
    def system_prompt(self) -> str:
        return """Ets un analista literari expert especialitzat en preparar textos per a traducció.

EL TEU OBJECTIU és analitzar un text original per identificar tot el que un traductor necessita saber ABANS de començar a traduir, per evitar traduccions literals i preservar la veu de l'autor.

══════════════════════════════════════════════════════════════════════════════
QUÈ HAS D'IDENTIFICAR
══════════════════════════════════════════════════════════════════════════════

1. PARAULES CLAU I TERMES CRÍTICS
   - Conceptes centrals que vertebren el text
   - Termes tècnics o especialitzats
   - Culturemes (elements culturals sense equivalent directe)
   - Noms propis i la seva forma adequada
   - Expressions idiomàtiques
   - Ambigüitats intencionals que cal preservar

   Per cada terme, indica:
   - Categoria (concepte_central, terme_tecnic, culturema, nom_propi, expressio_idiomatica, ambiguitat_intencional)
   - Importància (critica, alta, mitjana)
   - Recomanació de com tractar-lo

2. TO I VEU DE L'AUTOR
   - El to general (irònic, solemne, humorístic, distant, íntim...)
   - El registre (formal, informal, literari, col·loquial, tècnic, solemne)
   - L'actitud vers el lector (didàctica, còmplice, provocadora...)
   - Idiosincràsies estilístiques (tics, manies, repeticions característiques)

3. RECURSOS LITERARIS
   - Metàfores i comparacions
   - Figures de repetició (anàfora, paral·lelisme, al·literació)
   - Figures de pensament (ironia, antítesi, hipèrbole)
   - Jocs de paraules
   - Ritme i cadència (frases curtes/llargues, pauses)
   - Rima (si n'hi ha)

   Per cada recurs, indica l'estratègia de traducció recomanada.

4. REPTES DE TRADUCCIÓ ANTICIPATS
   - Estructures sintàctiques problemàtiques
   - Elements culturals difícils de traslladar
   - Ambigüitats que cal decidir si preservar
   - Referències intertextuals o al·lusions
   - Jocs de paraules intraduïbles
   - Registres o dialectes especials

5. RECOMANACIONS GENERALS
   - Què prioritzar (veu, fidelitat, ritme...)
   - Què evitar (calcs típics, errors comuns amb aquesta llengua)
   - Estratègia global suggerida

══════════════════════════════════════════════════════════════════════════════
GUIA PER LLENGUA
══════════════════════════════════════════════════════════════════════════════

LLATÍ:
- Atenció a l'ordre lliure de paraules (hipèrbaton)
- Ablatius absoluts: buscar equivalents naturals
- Períodes llargs: decidir si trencar o mantenir
- Lèxic filosòfic: consistència terminològica

GREC CLÀSSIC:
- Partícules (μέν...δέ, γάρ, οὖν): traduir funció, no forma
- Compostos: evitar monstres lèxics
- Ritme de la prosa àtica

JAPONÈS:
- Keigo: identificar nivells de formalitat i estratègia
- Subjectes omesos: quan explicitar, quan mantenir
- Onomatopeies: estratègia de naturalització
- Ordre SOV: com fluir naturalment

ANGLÈS:
- Falsos amics ("actually", "eventually"...)
- Gerundis: alternatives en català
- Passives: quan activar

FRANCÈS:
- Calcs sintàctics a evitar ("c'est...qui")
- Falsos amics ("attendre", "assister"...)

ALEMANY:
- Compostos llargs: descompondre intel·ligentment
- Verbs finals: reordenar naturalment
- Subordinació extrema: simplificar si cal

══════════════════════════════════════════════════════════════════════════════
FORMAT DE RESPOSTA (JSON ESTRICTE)
══════════════════════════════════════════════════════════════════════════════

{
    "llengua_origen": "<llengua detectada>",
    "genere_detectat": "<narrativa|poesia|filosofia|teatre|assaig|epistolari|oratoria|historiografia|text_sagrat>",
    "registre": "<formal|informal|literari|col·loquial|tecnic|solemne>",

    "to_autor": "<descripció del to en 2-3 frases>",
    "estil_caracteristic": "<trets estilístics distintius en 2-3 frases>",
    "ritme_cadencia": "<descripció del ritme i cadència>",

    "paraules_clau": [
        {
            "terme": "<terme original>",
            "transliteracio": "<si cal, o null>",
            "categoria": "<concepte_central|terme_tecnic|culturema|nom_propi|expressio_idiomatica|ambiguitat_intencional>",
            "importancia": "<critica|alta|mitjana>",
            "context": "<on apareix>",
            "recomanacio_traduccio": "<com tractar-lo>"
        }
    ],

    "recursos_literaris": [
        {
            "tipus": "<metafora|comparacio|al·literacio|anafora|paral·lelisme|antitesi|ironia|hiperbole|metonimia|personificacio|repeticio|ritme|rima|ambiguitat|joc_paraules|altre>",
            "descripcio": "<què fa aquest recurs>",
            "exemple": "<fragment on apareix>",
            "estrategia_traduccio": "<com preservar-lo o adaptar-lo>"
        }
    ],

    "reptes_traduccio": [
        {
            "tipus": "<sintaxi|lexic|cultural|estilistic|ambiguitat|intertextualitat|registre|ritme_so|joc_paraules|referencia_obscura>",
            "descripcio": "<descripció del repte>",
            "fragment": "<fragment afectat>",
            "dificultat": "<alta|mitjana|baixa>",
            "estrategia_suggerida": "<com abordar-lo>"
        }
    ],

    "recomanacions_generals": "<paràgraf amb consells generals>",
    "que_evitar": ["<error 1 a evitar>", "<error 2>", "..."],
    "prioritats": ["<prioritat 1>", "<prioritat 2>", "<prioritat 3>"],

    "confianca": <0.0-1.0>
}

══════════════════════════════════════════════════════════════════════════════
IMPORTANT
══════════════════════════════════════════════════════════════════════════════

- Sigues CONCRET i ACCIONABLE: no diguis "tenir cura amb el to", digues "preservar la ironia subtil del narrador quan critica X"
- Limita't a 5-10 paraules clau (les més importants)
- Limita't a 3-7 recursos literaris (els més rellevants)
- Limita't a 3-5 reptes (els més difícils)
- Les recomanacions han de ser específiques per aquest text, no genèriques"""

    def analitzar(
        self,
        text: str,
        llengua_origen: str = "llatí",
        autor: str | None = None,
        obra: str | None = None,
        genere: str | None = None,
    ) -> AnalisiPreTraduccio:
        """Analitza un text abans de traduir-lo.

        Args:
            text: Text original a analitzar.
            llengua_origen: Llengua del text.
            autor: Autor de l'obra (opcional).
            obra: Títol de l'obra (opcional).
            genere: Gènere literari (opcional, es detectarà automàticament).

        Returns:
            AnalisiPreTraduccio amb tota la informació identificada.
        """
        prompt_parts = [
            f"Analitza aquest text en {llengua_origen} per preparar una traducció al català.",
        ]

        if autor:
            prompt_parts.append(f"\nAutor: {autor}")
        if obra:
            prompt_parts.append(f"Obra: {obra}")
        if genere:
            prompt_parts.append(f"Gènere: {genere}")

        prompt_parts.extend([
            f"\n\n═══ TEXT A ANALITZAR ({llengua_origen.upper()}) ═══",
            text[:10000],  # Límit per evitar excés de tokens
        ])

        response = self.process("\n".join(prompt_parts))

        # Parsejar resposta JSON (robust)
        data = extract_json_from_text(response.content)
        if data:
            try:
                return self._parse_analisi(data, llengua_origen)
            except Exception as e:
                self.log_warning(f"Error parsejant anàlisi: {e}")

        # Retornar anàlisi per defecte (no bloqueja el pipeline)
        self.log_warning("No s'ha pogut parsejar JSON, continuant sense anàlisi detallada")
        return AnalisiPreTraduccio(
            llengua_origen=llengua_origen,
            to_autor="",
            recomanacions_generals="",
            confianca=0.5,
        )

    def _parse_analisi(self, data: dict, llengua_default: str) -> AnalisiPreTraduccio:
        """Parseja el diccionari de resposta a AnalisiPreTraduccio."""

        # Parsejar paraules clau
        paraules_clau = []
        for p in data.get("paraules_clau", []):
            try:
                paraules_clau.append(ParaulaClau(
                    terme=p.get("terme", ""),
                    transliteracio=p.get("transliteracio"),
                    categoria=p.get("categoria", "concepte_central"),
                    importancia=p.get("importancia", "alta"),
                    context=p.get("context", ""),
                    recomanacio_traduccio=p.get("recomanacio_traduccio", ""),
                ))
            except Exception:
                continue

        # Parsejar recursos literaris
        recursos = []
        for r in data.get("recursos_literaris", []):
            try:
                recursos.append(RecursLiterari(
                    tipus=r.get("tipus", "altre"),
                    descripcio=r.get("descripcio", ""),
                    exemple=r.get("exemple", ""),
                    estrategia_traduccio=r.get("estrategia_traduccio", ""),
                ))
            except Exception:
                continue

        # Parsejar reptes
        reptes = []
        for r in data.get("reptes_traduccio", []):
            try:
                reptes.append(RepteTraduccio(
                    tipus=r.get("tipus", "lexic"),
                    descripcio=r.get("descripcio", ""),
                    fragment=r.get("fragment", ""),
                    dificultat=r.get("dificultat", "mitjana"),
                    estrategia_suggerida=r.get("estrategia_suggerida", ""),
                ))
            except Exception:
                continue

        return AnalisiPreTraduccio(
            llengua_origen=data.get("llengua_origen", llengua_default),
            genere_detectat=data.get("genere_detectat", "narrativa"),
            registre=data.get("registre", "literari"),
            to_autor=data.get("to_autor", ""),
            estil_caracteristic=data.get("estil_caracteristic", ""),
            ritme_cadencia=data.get("ritme_cadencia", ""),
            paraules_clau=paraules_clau,
            recursos_literaris=recursos,
            reptes_traduccio=reptes,
            recomanacions_generals=data.get("recomanacions_generals", ""),
            que_evitar=data.get("que_evitar", []),
            prioritats=data.get("prioritats", []),
            confianca=data.get("confianca", 0.8),
        )

    def preparar_context(
        self,
        text: str,
        llengua_origen: str = "llatí",
        autor: str | None = None,
        obra: str | None = None,
        genere: str | None = None,
        glossari: dict[str, str] | None = None,
        exemples_fewshot: list[dict] | None = None,
    ) -> ContextTraduccioEnriquit:
        """Analitza i prepara el context complet per a la traducció.

        Mètode de conveniència que combina l'anàlisi amb glossari i exemples.

        Args:
            text: Text original.
            llengua_origen: Llengua del text.
            autor: Autor (opcional).
            obra: Obra (opcional).
            genere: Gènere (opcional).
            glossari: Glossari de termes (opcional).
            exemples_fewshot: Exemples de traduccions similars (opcional).

        Returns:
            ContextTraduccioEnriquit llest per passar al traductor.
        """
        # Analitzar el text
        analisi = self.analitzar(
            text=text,
            llengua_origen=llengua_origen,
            autor=autor,
            obra=obra,
            genere=genere,
        )

        return ContextTraduccioEnriquit(
            text_original=text,
            llengua_origen=llengua_origen,
            autor=autor,
            obra=obra,
            genere=genere or analisi.genere_detectat,
            analisi=analisi,
            exemples_fewshot=exemples_fewshot or [],
            glossari=glossari,
        )


class SelectorExemplesFewShot:
    """Selecciona exemples few-shot rellevants per a una traducció.

    Busca exemples de traduccions de qualitat similars al text a traduir,
    basant-se en llengua, gènere i autor.
    """

    def __init__(self, corpus_path: str | None = None):
        """Inicialitza el selector.

        Args:
            corpus_path: Ruta al directori amb els corpus d'exemples YAML.
                        Si no s'especifica, busca a 'exemples/' relatiu al projecte.
        """
        import os
        if corpus_path is None:
            # Buscar directori exemples relatiu al projecte
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            corpus_path = os.path.join(project_root, "exemples")

        self.corpus_path = corpus_path
        self._cache: dict[str, list[dict]] = {}

    def _carregar_corpus(self, fitxer: str) -> list[dict]:
        """Carrega un fitxer YAML de corpus."""
        if fitxer in self._cache:
            return self._cache[fitxer]

        import os
        filepath = os.path.join(self.corpus_path, fitxer)

        if not os.path.exists(filepath):
            return []

        try:
            import yaml
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                exemples = data.get("exemples", [])
                self._cache[fitxer] = exemples
                return exemples
        except Exception:
            return []

    def seleccionar(
        self,
        llengua_origen: str,
        genere: str,
        autor: str | None = None,
        max_exemples: int = 5,
    ) -> list[dict]:
        """Selecciona exemples rellevants.

        Args:
            llengua_origen: Llengua del text a traduir.
            genere: Gènere literari.
            autor: Autor (opcional, per buscar exemples del mateix autor).
            max_exemples: Nombre màxim d'exemples a retornar.

        Returns:
            Llista d'exemples amb camps 'original', 'traduccio', i opcionalment 'notes'.
        """
        exemples = []

        # Normalitzar llengua
        llengua_norm = llengua_origen.lower().replace("à", "a").replace("è", "e")

        # Fitxers a provar (de més a menys específic)
        fitxers_candidats = [
            f"{genere}_{llengua_norm}.yml",
            f"{llengua_norm}_{genere}.yml",
            f"{llengua_norm}.yml",
            f"{genere}.yml",
        ]

        if autor:
            autor_norm = autor.lower().replace(" ", "_")
            fitxers_candidats.insert(0, f"{autor_norm}.yml")

        # Carregar exemples dels fitxers que existeixin
        for fitxer in fitxers_candidats:
            corpus_exemples = self._carregar_corpus(fitxer)
            for ex in corpus_exemples:
                if ex not in exemples:
                    exemples.append(ex)
                if len(exemples) >= max_exemples:
                    return exemples[:max_exemples]

        return exemples[:max_exemples]

    def afegir_exemple(
        self,
        fitxer: str,
        original: str,
        traduccio: str,
        notes: str | None = None,
    ) -> bool:
        """Afegeix un exemple al corpus.

        Args:
            fitxer: Nom del fitxer YAML on afegir.
            original: Text original.
            traduccio: Traducció de qualitat.
            notes: Notes explicatives (opcional).

        Returns:
            True si s'ha afegit correctament.
        """
        import os
        import yaml

        filepath = os.path.join(self.corpus_path, fitxer)

        # Carregar o crear
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
        else:
            os.makedirs(self.corpus_path, exist_ok=True)
            data = {"descripcio": f"Exemples de traducció per {fitxer}", "exemples": []}

        # Afegir exemple
        exemple = {"original": original, "traduccio": traduccio}
        if notes:
            exemple["notes"] = notes

        if "exemples" not in data:
            data["exemples"] = []
        data["exemples"].append(exemple)

        # Guardar
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
            # Invalidar cache
            if fitxer in self._cache:
                del self._cache[fitxer]
            return True
        except Exception:
            return False
