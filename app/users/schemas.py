from typing import Optional

from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str

    class Config:
        orm_mode = True


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


class UserCreate(BaseModel):
    username: str
    email: Optional[str] | None = None
    password: str | None = None
    pass


class UserInDB(User):
    password: str | None = None
    id: int | None = None

    class Config:
        orm_mode = True
