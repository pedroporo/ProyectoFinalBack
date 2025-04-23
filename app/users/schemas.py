from datetime import datetime

from pydantic import BaseModel
from typing import Optional
import json
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    email: Optional[str] | None = None
    role: Optional[str] | None = None
    avatar: Optional[str] | None = None
    google_id: Optional[str] | None = None
    config_user: Optional[object] | None = None
    disabled: bool | None = False

    class Config:
        orm_mode = True


class UserCreate(User):
    pass


class UserInDB(User):
    password: str | None = None
    id: int | None = None

    class Config:
        orm_mode = True
