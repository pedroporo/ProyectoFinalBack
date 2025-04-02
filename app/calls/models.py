import os
import json
import enum
from sqlalchemy import Column
from twilio.rest import Client
from dotenv import load_dotenv
import re
import time
import  sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, mapped_column
#from app.db.session import Base
load_dotenv()
# Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
PHONE_NUMBER_FROM = os.getenv('TWILIO_NUMBER')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
raw_domain = os.getenv('DOMAIN', '')
MYSQL_DATABASE=os.getenv('MYSQL_DATABASE')
DOMAIN = re.sub(r'(^\w+:|^)\/\/|\/+$', '', raw_domain)  # Strip protocols and trailing slashes from DOMAIN

Base=declarative_base()


class Call(Base):
    __tablename__='calls'
    from ..agents.models import Agent

    id=Column(sqlalchemy.Integer,primary_key=True,index=True)
    contact_name=Column(sqlalchemy.String(40),nullable=False)
    phone_number=Column(sqlalchemy.String(20),nullable=False)
    call_id=Column(sqlalchemy.String(60),nullable=True)
    status=Column(sqlalchemy.String(20),default="ready",server_default="ready")
    call_date=Column(sqlalchemy.DateTime,nullable=True)
    call_duration=Column(sqlalchemy.Integer,nullable=True)
    call_json_twilio=Column(sqlalchemy.JSON,nullable=True)
    agent_id=Column(sqlalchemy.Integer,sqlalchemy.ForeignKey(Agent.id,ondelete='CASCADE',onupdate='CASCADE'),nullable=False)
    #agent = relationship("Agent", back_populates="calls")


    def to_dict(self):
        """Convierte la instancia del modelo a un diccionario serializable"""
        return {
            'id': self.id,
            'contact_name': self.contact_name,
            'phone_number':self.phone_number,
            'call_id':self.call_id,
            'status':self.status,
            'call_date':self.call_date,
            'call_duration':self.call_duration,
            'call_json_twilio':self.call_json_twilio,
            'agent_id':self.agent_id,
        }

    def toJSON(self):

        return json.dumps(self.to_dict(), indent=4)
