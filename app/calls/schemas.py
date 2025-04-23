from datetime import datetime

from pydantic import BaseModel
from typing import Optional


class CallBase(BaseModel):
    contact_name: str
    phone_number: str
    call_id: Optional[str] = None
    status: Optional[str] = "ready"
    call_date: Optional[datetime] = None
    call_duration: Optional[int] = None
    call_json_twilio: Optional[object] = None
    agent_id: int


class CallCreate(CallBase):
    pass


class CallResponse(CallBase):
    id: int

    class Config:
        orm_mode = True
