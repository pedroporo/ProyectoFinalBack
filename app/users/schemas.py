from datetime import datetime

from pydantic import BaseModel
from typing import Optional

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
    email: str | None = None
    role: str | None = None
    avatar: str | None = None
    google_id: str | None = None
    disabled: bool | None = None


class UserInDB(User):
    password: str
