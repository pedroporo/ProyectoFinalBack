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
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username": "admin",
                    "email": "admin@test.test",
                    "config_user": {
                        "database": {
                            'DB_USER': "default",
                            'DB_PASS': "default",
                            'DB_HOST': 'localhost',
                            'DB_PORT': 3306,
                            'DATABASE_NAME': 'Chatbot_app'
                        },
                        "credentials": {
                            "TWILIO_ACCOUNT_SID": '...',
                            "TWILIO_AUTH_TOKEN": '...',
                            'TWILIO_NUMBER': '+34555555',
                            'TWILIO_SERVICE_ID': 'dfss',
                            'OPENAI_API_KEY': '...'
                        },
                        "mail_settings": {
                            'MAIL_HOST': 'dfsf',
                            'MAIL_PORT': 465,
                            'MAIL_USERNAME': 'test@test.test',
                            'MAIL_PASSWORD': 'afdfsd',
                            'MAIL_RECIVERS': ["test@gmail.com", "test1@gmail.com"]
                        }
                    }
                }
            ]
        }
    }


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
