from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class TipusCalc(str):
    """Subtipus de str per compatibilitat d'imports amb plugins.

    La versió completa amb valors Enum és a utils/detector_calcs.py.
    """


class CalcDetectat(BaseModel):
    tipus: str
    text_original: str
    posicio: tuple[int, int]
    explicacio: str
    suggeriment: str
    severitat: float = Field(ge=0, le=10)
    llengua_origen: str | None = None


class DetectorPlugin(ABC):
    @property
    @abstractmethod
    def llengua(self) -> str:
        pass

    @abstractmethod
    def detectar(self, text: str) -> list[CalcDetectat]:
        pass
