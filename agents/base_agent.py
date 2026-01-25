"""Classe base abstracta per als agents de traducció."""

import time
from abc import ABC, abstractmethod
from typing import Any

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from utils.logger import AgentLogger, VerbosityLevel, get_logger


load_dotenv()


# Preus per milió de tokens (Claude Sonnet 4)
DEFAULT_INPUT_PRICE_PER_MILLION = 3.0  # USD
DEFAULT_OUTPUT_PRICE_PER_MILLION = 15.0  # USD
USD_TO_EUR = 0.92  # Conversió aproximada


class AgentConfig(BaseModel):
    """Configuració base per als agents."""

    model: str = Field(default="claude-sonnet-4-20250514")
    max_tokens: int = Field(default=4096)
    temperature: float = Field(default=0.3)


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

    def process(self, text: str, **kwargs: Any) -> AgentResponse:
        """Envia text a l'API i retorna la resposta.

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
