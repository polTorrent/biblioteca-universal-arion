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
        cmd = [
            "claude",
            "--print",  # Mode no interactiu
            "--output-format", "json",  # Resposta en JSON
            "--max-turns", "1",  # Limitar a una sola resposta
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

    def process(self, text: str, **kwargs: Any) -> AgentResponse:
        """Envia text a Claude i retorna la resposta.

        Args:
            text: El text a processar.
            **kwargs: Arguments addicionals pel missatge.

        Returns:
            AgentResponse amb el contingut i metadades.
        """
        # Log d'inici
        self.logger.log_start(self.agent_name, "Processant...")

        start_time = time.time()

        try:
            # MODE SUBSCRIPCIÓ: Usar claude CLI
            if self.use_subscription:
                self.logger.log_info(
                    self.agent_name,
                    "✅ Mode subscripció actiu - usant claude CLI"
                )

                response_data = self._call_claude_cli(
                    prompt=text,
                    system_prompt=self.system_prompt,
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
                message = self.client.messages.create(
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
