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
    phone_number: str
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Ana",
                    "voice": "alloy",
                    "description": "Una ia de indexeo",
                    "instrucciones": "Eres una ia servicial y deves tratar bien a los usuarios",
                    "empezar_ia": True,
                    "velozidadVoz": 1.0,
                    "creatividadVoz": 0.8,
                    "silenceCloseCall":30,
                    "callMaxDuration": 500,
                    "phone_number": "+3412312312"
                }
            ]
        }
    }

class AgentCreate(AgentBase):
    pass

class AgentResponse(AgentBase):
    id: int
    class Config:
        orm_mode = True