import json
import os
import re

import sqlalchemy
from dotenv import load_dotenv
from sqlalchemy import Column
from sqlalchemy import update, delete
from sqlalchemy.future import select
# from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.db import Base as Models_Base
from app.db import Users_Base as Base
from app.db.models import Database
# from app.db.session import get_db_session_class
from app.db.settings import local_db

# from app.db.session import Base
load_dotenv()
# Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
PHONE_NUMBER_FROM = os.getenv('TWILIO_NUMBER')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
raw_domain = os.getenv('DOMAIN', '')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE')
DOMAIN = re.sub(r'(^\w+:|^)\/\/|\/+$', '', raw_domain)  # Strip protocols and trailing slashes from DOMAIN
template_json_config = {
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
template_config_user = json.dumps(
    {
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
            'TWILIO_SERVICE_ID': 'dfss'
        },
        "mail_settings": {
            'MAIL_HOST': 'dfsf',
            'MAIL_PORT': 465,
            'MAIL_USERNAME': 'test@test.test',
            'MAIL_PASSWORD': 'afdfsd',
            'MAIL_RECIVERS': ["test@gmail.com", "test1@gmail.com"]
        }
    }
)


class User(Base):
    __tablename__ = 'users'

    id = Column(sqlalchemy.Integer, primary_key=True, index=True)
    username = Column(sqlalchemy.String(40), nullable=False)
    email = Column(sqlalchemy.String(70), nullable=False, unique=True)
    password = Column(sqlalchemy.String(60), nullable=True)
    role = Column(sqlalchemy.String(20), default="user", server_default="user")
    avatar = Column(sqlalchemy.Text, default="https://picsum.photos/200.jpg", nullable=True)
    google_id = Column(sqlalchemy.String(100), nullable=True, unique=True)
    config_user = Column(sqlalchemy.JSON, default=template_json_config, nullable=True)
    disabled = Column(sqlalchemy.Boolean, default=False, insert_default=False, server_default="0")

    def to_dict(self):
        """Convierte la instancia del modelo a un diccionario serializable"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'password': self.password,
            'role': self.role,
            'avatar': self.avatar,
            'google_id': self.google_id,
            'disabled': self.disabled,
            'config_user': self.config_user,
        }

    def toJSON(self):

        return json.dumps(self.to_dict(), indent=4)

    async def update(self):

        async with local_db.get_db_session_class() as s:
            mapped_values = {}
            for item in User.__dict__.items():
                field_name = item[0]
                field_type = item[1]
                is_column = isinstance(field_type, InstrumentedAttribute)
                if is_column:
                    mapped_values[field_name] = getattr(self, field_name)
            await s.execute(update(User).where(User.id == self.id).values(**mapped_values))
            await s.commit()

    async def delete(self):
        async with local_db.get_db_session_class() as s:
            await s.execute(delete(User).where(User.id == self.id))
            await s.commit()

    async def create(self):
        async with local_db.get_db_session_class() as s:
            # await s.add(self)
            s.add(self)
            await s.commit()
            await s.refresh(self)
            return await self.get()

    async def get(self):
        async with local_db.get_db_session_class() as s:
            result = await s.execute(select(User).where(User.username == self.username))
            return result.scalar()

    async def getByGId(self):
        async with local_db.get_db_session_class() as s:
            result = await s.execute(select(User).where(User.google_id == self.google_id))
            return result.scalar()

    async def get_user_database(self):
        # print(f'Config: {config["database"]}')
        db = Database(
            DB_USER=self.config_user["database"]["DB_USER"],
            DB_PASS=self.config_user["database"]["DB_PASS"],
            DB_HOST=self.config_user["database"]["DB_HOST"],
            DB_PORT=self.config_user["database"]["DB_PORT"],
            DATABASE_NAME=self.config_user["database"]["DATABASE_NAME"],
            BASE=Models_Base
        )
        await db.init()  # Requerido: crea la base de datos si no existe
        await db.init_models()  # Opcional: crea las tablas si no existen
        return db


class GoogleCredential(Base):
    __tablename__ = "google_credentials"

    user_id = Column(sqlalchemy.String(100), primary_key=True, index=True)
    access_token = Column(sqlalchemy.String(400), nullable=False)
    refresh_token = Column(sqlalchemy.String(400))
    expires_at = Column(sqlalchemy.DateTime, nullable=False)

    def to_dict(self):
        """Convierte la instancia del modelo a un diccionario serializable"""
        return {
            'user_id': self.user_id,
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'expires_at': self.expires_at.isoformat(),
        }

    def toJSON(self):
        return json.dumps(self.to_dict(), indent=4)

    async def update(self):

        async with local_db.get_db_session_class() as s:
            mapped_values = {}
            for item in GoogleCredential.__dict__.items():
                field_name = item[0]
                field_type = item[1]
                is_column = isinstance(field_type, InstrumentedAttribute)
                if is_column:
                    mapped_values[field_name] = getattr(self, field_name)
            await s.execute(
                update(GoogleCredential).where(GoogleCredential.user_id == self.user_id).values(**mapped_values))
            await s.commit()

    async def delete(self):
        async with local_db.get_db_session_class() as s:
            await s.execute(delete(GoogleCredential).where(GoogleCredential.user_id == self.user_id))
            await s.commit()

    async def create(self):
        async with local_db.get_db_session_class() as s:
            # await s.add(self)
            s.add(self)
            await s.commit()
            await s.refresh(self)
            return await self.get()

    async def get(self):
        # print(f'Database1: {local_db.to_dict()} \n UserGID: {self.user_id}')
        async with local_db.get_db_session_class() as s:
            result = await s.execute(select(GoogleCredential).where(GoogleCredential.user_id == self.user_id))
            return result.scalar()

    async def getFromUser(self, user_id):
        # print(f'DatabaseU: {local_db.to_dict()} \n UserGID: {user_id}')
        async with local_db.get_db_session_class() as s:
            result = await s.execute(select(GoogleCredential).where(GoogleCredential.user_id == user_id))
            return result.scalar()


class Issued_tokens(Base):
    __tablename__ = 'issued_tokens'

    id = Column(sqlalchemy.Integer, primary_key=True, index=True)
    token = Column(sqlalchemy.String(40), nullable=False)
    email_id = Column(sqlalchemy.String(20), nullable=False)
    session_id = Column(sqlalchemy.String(60), nullable=True)

    def to_dict(self):
        """Convierte la instancia del modelo a un diccionario serializable"""
        return {
            'id': self.id,
            'token': self.token,
            'email_id': self.email_id,
            'session_id': self.session_id,

        }

    def toJSON(self):

        return json.dumps(self.to_dict(), indent=4)

    async def update(self):

        async with local_db.get_db_session_class() as s:
            mapped_values = {}
            for item in Issued_tokens.__dict__.items():
                field_name = item[0]
                field_type = item[1]
                is_column = isinstance(field_type, InstrumentedAttribute)
                if is_column:
                    mapped_values[field_name] = getattr(self, field_name)
            await s.execute(update(Issued_tokens).where(Issued_tokens.id == self.id).values(**mapped_values))
            await s.commit()

    async def delete(self):
        async with local_db.get_db_session_class() as s:
            await s.execute(delete(Issued_tokens).where(Issued_tokens.id == self.id))
            await s.commit()

    async def create(self):

        async with local_db.get_db_session_class() as s:
            await s.add(self)
            await s.commit()
            await s.refresh(self)

    async def get(self):
        async with local_db.get_db_session_class() as s:
            result = await s.execute(select(Issued_tokens).where(Issued_tokens.id == self.id))
            return result.scalar()
