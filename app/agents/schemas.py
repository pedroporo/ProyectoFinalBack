from pydantic import BaseModel
from typing import Optional
from app.agents.models import VoiceOptionsEnum
from enum import Enum
class VoiceOptionsEnumStr(str, Enum):
    alloy = 'alloy'
    ash = 'ash'
    ballad = 'ballad'
    coral = 'coral'
    echo = 'echo'
    sage = 'sage'
    shimmer = 'shimmer'
    verse = 'verse'
class AgentBase(BaseModel):
    name: str
    #voice: VoiceOptionsEnumStr = VoiceOptionsEnum.alloy
    voice: str  # o usar VoiceOptionsEnum si quieres validación estricta
    descripcion: Optional[str] = None
    instrucciones: str
    empezar_ia: bool = True
    velozidadVoz: float = 1.0
    creatividadVoz: float = 0.6
    silenceCloseCall: int = 30
    callMaxDuration: Optional[int] = None

class AgentCreate(AgentBase):
    pass

class AgentResponse(AgentBase):
    id: int
    class Config:
        orm_mode = True