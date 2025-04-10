import os
import json
import enum
from sqlalchemy import Column, update
from twilio.rest import Client
from dotenv import load_dotenv
import re
import time
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete

from app.db.session import get_db_session

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

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(sqlalchemy.Integer, primary_key=True, index=True)
    username = Column(sqlalchemy.String(40), nullable=False)
    email = Column(sqlalchemy.String(70), nullable=False, unique=True)
    password = Column(sqlalchemy.String(60), nullable=True)
    role = Column(sqlalchemy.String(20), default="user", server_default="user")
    avatar = Column(sqlalchemy.String(4000), nullable=True)
    google_id = Column(sqlalchemy.String(3000), nullable=True, unique=True)
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
        }

    def toJSON(self):

        return json.dumps(self.to_dict(), indent=4)

    async def update(self):

        async with get_db_session() as s:
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
        async with get_db_session() as s:
            await s.execute(delete(User).where(User.id == self.id))
            await s.commit()

    async def create(self):
        async with get_db_session() as s:
            # await s.add(self)
            s.add(self)
            await s.commit()
            await s.refresh(self)
            return await self.get()

    async def get(self):
        async with get_db_session() as s:
            result = await s.execute(select(User).where(User.username == self.username))
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

        async with get_db_session() as s:
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
        async with get_db_session() as s:
            await s.execute(delete(Issued_tokens).where(Issued_tokens.id == self.id))
            await s.commit()

    async def create(self):

        async with get_db_session() as s:
            await s.add(self)
            await s.commit()
            await s.refresh(self)

    async def get(self):
        async with get_db_session() as s:
            result = await s.execute(select(Issued_tokens).where(Issued_tokens.id == self.id))
            return result.scalar()
