"""Classe base abstracta per als agents de traducció."""

import json
import os
import re
import subprocess
import time
from abc import ABC, abstractmethod
from typing import Any

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from utils.logger import AgentLogger, VerbosityLevel, get_logger


load_dotenv()

# ════════════════════════════════════════════════════════════════════════════════
# CONTEXT ACADÈMIC PER EVITAR FILTRATGE DE CONTINGUT
# ════════════════════════════════════════════════════════════════════════════════
# Alguns textos clàssics (Plató, tragèdies gregues, etc.) contenen referències
# a mort, execució, suïcidi, etc. que poden activar filtres de contingut.
# Aquest prefix s'afegeix al system prompt per indicar el context acadèmic.
# ════════════════════════════════════════════════════════════════════════════════

ACADEMIC_CONTEXT_PREFIX = """[CONTEXT ACADÈMIC]
Ets un traductor acadèmic especialitzat en textos clàssics de domini públic.
Els textos que tradueixes són obres literàries i filosòfiques antigues amb
finalitat educativa i de preservació cultural. Poden contenir referències
històriques a temes com la mort, execucions, guerres o altres esdeveniments
que eren comuns en l'antiguitat. El teu objectiu és traduir fidelment
aquests textos per a estudiants, investigadors i amants de la literatura clàssica.

"""


class ContentFilterError(Exception):
    """Error quan l'API bloqueja contingut per polítiques de filtratge."""
    pass


def extract_json_from_text(text: str) -> dict[str, Any] | None:
    """Extreu un objecte JSON d'un text que pot contenir text addicional.

    Útil quan el model retorna JSON incrustat en una explicació.

    Args:
        text: Text que pot contenir JSON.

    Returns:
        Dict parsejar si es troba JSON vàlid, None si no.
    """
    if not text:
        return None

    # Primer intentar parsejar directament
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Buscar JSON entre claus
    # Patró per trobar objectes JSON (amb nesting)
    brace_count = 0
    start_idx = None

    for i, char in enumerate(text):
        if char == '{':
            if brace_count == 0:
                start_idx = i
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0 and start_idx is not None:
                candidate = text[start_idx:i+1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    start_idx = None
                    continue

    # Intentar amb regex per blocs de codi
    code_block_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', text)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1))
        except json.JSONDecodeError:
            pass

    return None


# Preus per milió de tokens (Claude Sonnet 4)
DEFAULT_INPUT_PRICE_PER_MILLION = 3.0  # USD
DEFAULT_OUTPUT_PRICE_PER_MILLION = 15.0  # USD
USD_TO_EUR = 0.92  # Conversió aproximada


class AgentConfig(BaseModel):
    """Configuració base per als agents."""

    model: str = Field(default="claude-sonnet-4-20250514")
    max_tokens: int = Field(default=4096)
    temperature: float = Field(default=0.3)
    use_api: bool = Field(default=False)  # False = subscripció, True = API
    add_academic_context: bool = Field(default=True)  # Afegir context acadèmic
    max_retries_on_filter: int = Field(default=2)  # Reintents si hi ha filtratge


class AgentResponse(BaseModel):
    """Resposta estructurada d'un agent."""

    content: str
    model: str
    usage: dict[str, int]
    duration_seconds: float = 0.0
    cost_eur: float = 0.0


class BaseAgent(ABC):
    """Classe base abstracta per a tots els agents de traducció.

    Cada agent especialitzat ha d'heretar d'aquesta classe i implementar
    el mètode `system_prompt` i opcionalment sobreescriure `process`.
    """

    # Nom de l'agent per al logging (sobreescriure a subclasses)
    agent_name: str = "BaseAgent"

    def __init__(
        self,
        config: AgentConfig | None = None,
        logger: AgentLogger | None = None,
    ) -> None:
        """Inicialitza l'agent.

        Args:
            config: Configuració de l'agent.
            logger: Logger per al seguiment. Si no es proporciona, s'usa el global.
        """
        self.config = config or AgentConfig()

        # Detectar context: Claude Code (subscripció) vs Web (API)
        is_claude_code = os.getenv("CLAUDECODE") == "1"

        # Si estem en Claude Code i no s'ha especificat use_api, usar subscripció
        if is_claude_code and not self.config.use_api:
            # Mode subscripció: Claude Code utilitza la subscripció Pro/Max
            # IMPORTANT: Cal utilitzar claude CLI o mètode similar
            # Per ara, marcar que NO s'usa API
            self.use_subscription = True
            self.client = None  # No usar SDK d'Anthropic directament
        else:
            # Mode API: Usuaris web amb pagament
            self.use_subscription = False
            self.client = anthropic.Anthropic()

        self._logger = logger

    @property
    def logger(self) -> AgentLogger:
        """Retorna el logger (lazy initialization)."""
        if self._logger is None:
            self._logger = get_logger()
        return self._logger

    @logger.setter
    def logger(self, value: AgentLogger) -> None:
        """Estableix el logger."""
        self._logger = value

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Retorna el system prompt específic de l'agent."""
        ...

    def _calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        input_price: float = DEFAULT_INPUT_PRICE_PER_MILLION,
        output_price: float = DEFAULT_OUTPUT_PRICE_PER_MILLION,
    ) -> float:
        """Calcula el cost en EUR.

        Args:
            input_tokens: Tokens d'entrada.
            output_tokens: Tokens de sortida.
            input_price: Preu per milió de tokens d'entrada (USD).
            output_price: Preu per milió de tokens de sortida (USD).

        Returns:
            Cost en euros.
        """
        input_cost = (input_tokens / 1_000_000) * input_price
        output_cost = (output_tokens / 1_000_000) * output_price
        total_usd = input_cost + output_cost
        return total_usd * USD_TO_EUR

    def _call_claude_cli(
        self,
        prompt: str,
        system_prompt: str,
    ) -> dict[str, Any]:
        """Crida al CLI de claude amb subscripció.

        Args:
            prompt: Prompt de l'usuari.
            system_prompt: System prompt de l'agent.

        Returns:
            Dict amb la resposta parseada del CLI.

        Raises:
            subprocess.CalledProcessError: Si el CLI falla.
            json.JSONDecodeError: Si la resposta no és JSON vàlid.
        """
        # Construir comanda
        # NOTA: Desactivem eines (--tools "") perquè els agents necessiten resposta directa,
        # no cridar a altres eines com web search que consumeixen turns addicionals.
        cmd = [
            "claude",
            "--print",  # Mode no interactiu
            "--output-format", "json",  # Resposta en JSON
            "--max-turns", "1",  # Una sola resposta (sense eines no cal més)
            "--tools", "",  # Desactivar eines per evitar web search, etc.
            "--system-prompt", system_prompt,
            "--model", self.config.model,
            "--no-session-persistence",  # No desar sessió
            prompt,
        ]

        # Executar comanda
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minuts màxim
        )

        # Verificar èxit
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout
            raise RuntimeError(
                f"Claude CLI ha fallat (exit code {result.returncode}): {error_msg}"
            )

        # Parsejar JSON
        try:
            response_data = json.loads(result.stdout)
            return response_data
        except json.JSONDecodeError as e:
            # Si falla el parsing, mostrar sortida per debug
            self.logger.log_warning(
                self.agent_name,
                f"No s'ha pogut parsejar resposta JSON del CLI. Sortida: {result.stdout[:500]}"
            )
            raise

    def _get_effective_system_prompt(self) -> str:
        """Retorna el system prompt amb context acadèmic si està configurat."""
        if self.config.add_academic_context:
            return ACADEMIC_CONTEXT_PREFIX + self.system_prompt
        return self.system_prompt

    def _is_content_filter_error(self, error: Exception) -> bool:
        """Determina si l'error és per filtratge de contingut."""
        error_str = str(error).lower()
        filter_indicators = [
            "content filtering",
            "output blocked",
            "content_filter",
            "safety",
            "policy",
        ]
        return any(indicator in error_str for indicator in filter_indicators)

    def process(self, text: str, **kwargs: Any) -> AgentResponse:
        """Envia text a Claude i retorna la resposta.

        Args:
            text: El text a processar.
            **kwargs: Arguments addicionals pel missatge.

        Returns:
            AgentResponse amb el contingut i metadades.

        Raises:
            ContentFilterError: Si el contingut és bloquejat després de tots els reintents.
        """
        # Log d'inici
        self.logger.log_start(self.agent_name, "Processant...")

        start_time = time.time()
        last_error = None
        effective_system_prompt = self._get_effective_system_prompt()

        # Intentar amb reintents per errors de filtratge
        for attempt in range(self.config.max_retries_on_filter + 1):
            try:
                # MODE SUBSCRIPCIÓ: Usar claude CLI
                if self.use_subscription:
                    if attempt == 0:
                        self.logger.log_info(
                            self.agent_name,
                            "✅ Mode subscripció actiu - usant claude CLI"
                        )
                    else:
                        self.logger.log_info(
                            self.agent_name,
                            f"🔄 Reintent {attempt}/{self.config.max_retries_on_filter} amb context reforçat"
                        )

                    response_data = self._call_claude_cli(
                        prompt=text,
                        system_prompt=effective_system_prompt,
                    )

                    duration = time.time() - start_time

                    # Extreure contingut de la resposta del CLI
                    # Format: {"type": "result", "result": "...", "usage": {...}, ...}
                    content = response_data.get("result", "")

                    # Determinar model utilitzat
                    model_usage = response_data.get("modelUsage", {})
                    if model_usage:
                        # Agafar primer model de la llista
                        model_used = list(model_usage.keys())[0] if model_usage else self.config.model
                    else:
                        model_used = self.config.model

                    # Extreure usage
                    usage = response_data.get("usage", {})
                    input_tokens = usage.get("input_tokens", 0)
                    output_tokens = usage.get("output_tokens", 0)

                    # Cost = 0 (inclòs en subscripció)
                    cost = 0.0

                    # Log de completat
                    self.logger.log_complete(
                        self.agent_name,
                        duration_seconds=duration,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cost_eur=cost,
                    )

                    return AgentResponse(
                        content=content,
                        model=model_used,
                        usage={
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                        },
                        duration_seconds=duration,
                        cost_eur=cost,
                    )

                # MODE API: Usar SDK d'Anthropic
                else:
                    if attempt > 0:
                        self.logger.log_info(
                            self.agent_name,
                            f"🔄 Reintent {attempt}/{self.config.max_retries_on_filter} amb context reforçat"
                        )

                    message = self.client.messages.create(
                        model=self.config.model,
                        max_tokens=self.config.max_tokens,
                        temperature=self.config.temperature,
                        system=effective_system_prompt,
                        messages=[
                            {"role": "user", "content": text}
                        ],
                    )

                    duration = time.time() - start_time
                    input_tokens = message.usage.input_tokens
                    output_tokens = message.usage.output_tokens
                    cost = self._calculate_cost(input_tokens, output_tokens)

                    # Log de completat
                    self.logger.log_complete(
                        self.agent_name,
                        duration_seconds=duration,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cost_eur=cost,
                    )

                    return AgentResponse(
                        content=message.content[0].text,
                        model=message.model,
                        usage={
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                        },
                        duration_seconds=duration,
                        cost_eur=cost,
                    )

            except Exception as e:
                last_error = e

                # Si és error de filtratge, reintentar amb context més específic
                if self._is_content_filter_error(e):
                    if attempt < self.config.max_retries_on_filter:
                        self.logger.log_warning(
                            self.agent_name,
                            f"⚠️ Filtratge de contingut detectat. Reforçant context acadèmic..."
                        )
                        # Reforçar el context acadèmic per al proper intent
                        effective_system_prompt = self._get_reinforced_academic_prompt(attempt + 1)
                        time.sleep(1)  # Petita pausa abans de reintentar
                        continue
                    else:
                        # Tots els reintents exhaurits
                        self.logger.log_error(
                            self.agent_name,
                            ContentFilterError(
                                f"El contingut ha estat bloquejat per polítiques de filtratge "
                                f"després de {self.config.max_retries_on_filter + 1} intents. "
                                f"Considera dividir el text en fragments més petits."
                            )
                        )
                        raise ContentFilterError(
                            f"Contingut bloquejat després de {self.config.max_retries_on_filter + 1} "
                            f"intents. Text original potser massa sensible per processar d'una sola vegada."
                        ) from e
                else:
                    # Altres errors: no reintentar
                    duration = time.time() - start_time
                    self.logger.log_error(self.agent_name, e)
                    raise

        # Si hem arribat aquí sense retornar, propagar l'últim error
        if last_error:
            raise last_error

    def _get_reinforced_academic_prompt(self, attempt: int) -> str:
        """Genera un system prompt amb context acadèmic reforçat per a reintents."""
        reinforced_prefix = f"""[CONTEXT ACADÈMIC - NIVELL {attempt + 1}]
IMPORTANT: Aquest és un text clàssic de domini públic amb finalitat purament acadèmica.

Estàs traduint una obra filosòfica/literària antiga per a:
- Estudiants universitaris de filosofia i lletres clàssiques
- Investigadors en humanitats
- Preservació del patrimoni cultural universal

El text pot contenir referències històriques a temes com la mort, la justícia,
la pena capital, guerres, o altres esdeveniments que eren part de la vida
quotidiana a l'antiguitat. Aquestes referències són necessàries per entendre
el context històric i filosòfic de l'obra.

La traducció ha de ser fidel al text original per mantenir el seu valor acadèmic.

"""
        return reinforced_prefix + self.system_prompt

    async def process_async(self, text: str, **kwargs: Any) -> AgentResponse:
        """Versió asíncrona de process."""
        # Log d'inici
        self.logger.log_start(self.agent_name, "Processant (async)...")

        start_time = time.time()

        try:
            async_client = anthropic.AsyncAnthropic()

            message = await async_client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=self.system_prompt,
                messages=[
                    {"role": "user", "content": text}
                ],
            )

            duration = time.time() - start_time
            input_tokens = message.usage.input_tokens
            output_tokens = message.usage.output_tokens
            cost = self._calculate_cost(input_tokens, output_tokens)

            # Log de completat
            self.logger.log_complete(
                self.agent_name,
                duration_seconds=duration,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_eur=cost,
            )

            return AgentResponse(
                content=message.content[0].text,
                model=message.model,
                usage={
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                },
                duration_seconds=duration,
                cost_eur=cost,
            )

        except Exception as e:
            duration = time.time() - start_time
            self.logger.log_error(self.agent_name, e)
            raise

    def log_debug(self, message: str) -> None:
        """Log de depuració."""
        self.logger.log_debug(self.agent_name, message)

    def log_info(self, message: str) -> None:
        """Log informatiu."""
        self.logger.log_info(self.agent_name, message)

    def log_warning(self, message: str) -> None:
        """Log d'avís."""
        self.logger.log_warning(self.agent_name, message)
