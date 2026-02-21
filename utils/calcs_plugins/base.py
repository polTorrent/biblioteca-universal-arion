from abc import ABC, abstractmethod
from typing import List
from pydantic import BaseModel, Field

class TipusCalc(str):
    pass

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
    def detectar(self, text: str) -> List[CalcDetectat]:
        pass
