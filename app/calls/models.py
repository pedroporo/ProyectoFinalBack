import json
import os
import re
from datetime import datetime

import sqlalchemy
from dotenv import load_dotenv
from sqlalchemy import Column
from sqlalchemy import update, delete
from sqlalchemy.future import select
# from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.db import Base
from app.db.context import get_current_db

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


# Base = declarative_base()


class Call(Base):
    __tablename__ = 'calls'
    from ..agents.models import Agent

    id = Column(sqlalchemy.Integer, primary_key=True, index=True)
    contact_name = Column(sqlalchemy.String(40), nullable=False)
    phone_number = Column(sqlalchemy.String(20), nullable=False)
    call_id = Column(sqlalchemy.String(60), nullable=True)
    status = Column(sqlalchemy.String(20), default="ready", server_default="ready")
    call_date = Column(sqlalchemy.DateTime, nullable=True)
    call_duration = Column(sqlalchemy.Integer, nullable=True)
    call_json_twilio = Column(sqlalchemy.JSON, nullable=True)
    agent_id = Column(sqlalchemy.Integer, sqlalchemy.ForeignKey(Agent.id, ondelete='CASCADE', onupdate='CASCADE'),
                      nullable=False)

    # agent = relationship("Agent", back_populates="calls")

    def to_dict(self):
        """Convierte la instancia del modelo a un diccionario serializable"""
        return {
            'id': self.id,
            'contact_name': self.contact_name,
            'phone_number': self.phone_number,
            'call_id': self.call_id,
            'status': self.status,
            'call_date': self.call_date,
            'call_duration': self.call_duration,
            'call_json_twilio': self.call_json_twilio,
            'agent_id': self.agent_id,
        }

    def toJSON(self):

        return json.dumps(self.to_dict(), indent=4, sort_keys=True, default=str)

    async def update(self):
        db = get_current_db()
        async with db.get_db_session_class() as s:
            mapped_values = {}
            for item in Call.__dict__.items():
                field_name = item[0]
                field_type = item[1]
                is_column = isinstance(field_type, InstrumentedAttribute)
                if is_column:
                    mapped_values[field_name] = getattr(self, field_name)
            await s.execute(update(Call).where(Call.id == self.id).values(**mapped_values))
            await s.commit()

    async def delete(self):
        db = get_current_db()
        async with db.get_db_session_class() as s:
            await s.execute(delete(Call).where(Call.id == self.id))
            await s.commit()

    async def create(self):
        db = get_current_db()
        async with db.get_db_session_class() as s:
            s.add(self)
            await s.commit()
            await s.refresh(self)

    async def get(self):
        db = get_current_db()
        async with db.get_db_session_class() as s:
            result = await s.execute(select(Call).where(Call.id == self.id))
            return result.scalar()

    async def getBySid(self):
        db = get_current_db()
        async with db.get_db_session_class() as s:
            result = await s.execute(select(Call).where(Call.call_id == self.call_id))
            return result.scalar()


class Transcription(Base):
    __tablename__ = "transcriptions"
    id = Column(sqlalchemy.Integer, primary_key=True)
    call_id = Column(sqlalchemy.String(60))
    content = Column(sqlalchemy.Text)
    created_at = Column(sqlalchemy.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convierte la instancia del modelo a un diccionario serializable"""
        return {
            'id': self.id,
            'call_id': self.call_id,
            'content': self.content,
            'created_at': self.created_at,
        }

    def toJSON(self):

        return json.dumps(self.to_dict(), indent=4)

    async def update(self):
        db = get_current_db()
        async with db.get_db_session_class() as s:
            mapped_values = {}
            for item in Transcription.__dict__.items():
                field_name = item[0]
                field_type = item[1]
                is_column = isinstance(field_type, InstrumentedAttribute)
                if is_column:
                    mapped_values[field_name] = getattr(self, field_name)
            await s.execute(update(Transcription).where(Transcription.id == self.id).values(**mapped_values))
            await s.commit()

    async def delete(self):
        db = get_current_db()
        async with db.get_db_session_class() as s:
            await s.execute(delete(Transcription).where(Transcription.id == self.id))
            await s.commit()

    async def create(self):
        db = get_current_db()
        async with db.get_db_session_class() as s:
            s.add(self)
            await s.commit()
            await s.refresh(self)

    async def get(self):
        db = get_current_db()
        async with db.get_db_session_class() as s:
            result = await s.execute(select(Transcription).where(Transcription.id == self.id))
            return result.scalar()

    async def getBySid(self):
        db = get_current_db()
        async with db.get_db_session_class() as s:
            result = await s.execute(select(Transcription).where(Transcription.call_id == self.call_id))
            return result.scalar()
