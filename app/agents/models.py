import os
import json
import enum
import asyncio
from fastapi import Depends
import httpx
from sqlalchemy import Column
from sqlalchemy.future import select
import  sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.future import select
from sqlalchemy import update,delete
#from main import call_id
from twilio.rest import Client
from dotenv import load_dotenv
import re
import time

#from websocket_server.server import Server
#from websocket_server.sessionManager import SessionManager

from app.db.session import get_db_session

#from app.db.session import Base

load_dotenv()
# Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
PHONE_NUMBER_FROM = os.getenv('TWILIO_NUMBER')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
raw_domain = os.getenv('DOMAIN', '')
DOMAIN = re.sub(r'(^\w+:|^)\/\/|\/+$', '', raw_domain)
PORT = int(os.getenv('PORT', 8765))
Base=declarative_base()


class VoiceOptionsEnum(enum.Enum):
    alloy = 'alloy'
    ash = 'ash'
    ballad='ballad'
    coral='coral'
    echo='echo'
    sage='sage'
    shimmer='shimmer'
    verse='verse'

class Agent(Base):
    __tablename__='agents'

    id=Column(sqlalchemy.Integer,primary_key=True,index=True)
    name=Column(sqlalchemy.String(20),nullable=False)
    voice=Column(sqlalchemy.Enum(VoiceOptionsEnum),nullable=False,default=VoiceOptionsEnum.alloy,server_default=VoiceOptionsEnum.alloy.value)
    descripcion=Column(sqlalchemy.String(300),nullable=True)
    instrucciones=Column(sqlalchemy.String(65535),nullable=False)
    empezar_ia=Column(sqlalchemy.Boolean,nullable=False,default=True)
    velozidadVoz=Column(sqlalchemy.Float,default=1)
    creatividadVoz=Column(sqlalchemy.Float,default=0.6)
    silenceCloseCall=Column(sqlalchemy.Integer,default=30)
    callMaxDuration=Column(sqlalchemy.Integer)
    #calls= relationship("Call", back_populates="agent", cascade="all, delete-orphan")
    async def update(self):
        #s = get_db_session()
        async with get_db_session() as s:
            mapped_values = {}
            for item in Agent.__dict__.items():
                field_name = item[0]
                field_type = item[1]
                is_column = isinstance(field_type, InstrumentedAttribute)
                if is_column:
                    mapped_values[field_name] = getattr(self, field_name)

        #s.query(Call).filter(Call.call_id == self.call_id).update(mapped_values)
            await s.execute(update(Agent).where(Agent.id == self.id).values(**mapped_values))
            await s.commit()
    async def delete(self):
        #s = get_db_session()
        async with get_db_session() as s:
            await s.execute(delete(Agent).where(Agent.id == self.id))
            await s.commit()
    async def create(self):
        #s = get_db_session()
        async with get_db_session() as s:
            await s.add(self)
            await s.commit()
            await s.refresh(self)
    def to_dict(self):
        """Convierte la instancia del modelo a un diccionario serializable"""
        return {
            'id': self.id,
            'name': self.name,
            'voice': self.voice.value if self.voice else None,
            'descripcion': self.descripcion,
            'instrucciones': self.instrucciones,
            'empezar_ia': self.empezar_ia,
            'velozidadVoz': self.velozidadVoz,
            'creatividadVoz': self.creatividadVoz,
            'silenceCloseCall': self.silenceCloseCall,
            'callMaxDuration': self.callMaxDuration
        }

    def toJSON(self):
        return json.dumps(self.to_dict(), indent=4)

    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and PHONE_NUMBER_FROM and OPENAI_API_KEY):
        raise ValueError('Missing Twilio and/or OpenAI environment variables. Please set them in the .env file.')

    # Initialize Twilio client


    async def check_number_allowed(self,to):
        try:
            # Saltarse el filtro de llamaddas
            # OVERRIDE_NUMBERS = ['+34653072842','+34678000893','+34642447846']
            # if to in OVERRIDE_NUMBERS:
            # return True
            return True
            incoming_numbers = client.incoming_phone_numbers.list(phone_number=to)
            if incoming_numbers:
                return True

            outgoing_caller_ids = client.outgoing_caller_ids.list(phone_number=to)
            if outgoing_caller_ids:
                return True

            return False
        except Exception as e:
            print(f"Error checking phone number: {e}")
            return False

    async def make_call(self, db):
    #async def make_call(self,phone_number_to_call: str):
        """Make an outbound call."""
        #if not phone_number_to_call:
        #    raise ValueError("Please provide a phone number to call.")
        from ..calls.models import Call
        #db = await anext(get_db_session())
        #db=get_db_session()

        #result = await db.execute(select(Call).where(Call.agent_id == self.id and Call.status == "ready"))

        result = await db.execute(select(Call).where(sqlalchemy.and_(Call.agent_id == self.id , Call.status == "ready")))
        numeros = result.scalars().all()
        print(numeros)

        #print(payload)
        headers = {
            'Content-Type': 'application/json',
        }

        #response = requests.request("POST", f'https://{DOMAIN}/setSession/',headers=headers, data=payload,json=payload,allow_redirects=True)


        #response = requests.request("POST", f'https://{DOMAIN}/setSession/', headers=headers, json=self.to_dict(),allow_redirects=True,verify=False)
        #print(response.text)
        #Server.session_manager=SessionManager(VOICE=self.voice.value,SYSTEM_MESSAGE=self.instrucciones,CREATIVITY=self.creatividadVoz)
        #is_allowed = await self.check_number_allowed(phone_number_to_call)
        #if not is_allowed:
        #    raise ValueError(
        #        f"The number {phone_number_to_call} is not recognized as a valid outgoing number or caller ID.")

        # Ensure compliance with applicable laws and regulations
        # All of the rules of TCPA apply even if a call is made by AI.
        # Do your own diligence for compliance.

        self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        outbound_twiml = (
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<Response><Connect><Stream url="wss://{DOMAIN}/media-stream" /> </Connect><Pause length="{self.silenceCloseCall}"/><Hangup/></Response>'
        )
        for phone_number_to_call in numeros:

            #test=str(self.instrucciones).format(customer_name=phone_number_to_call.contact_name)
            #print(self.instrucciones.format(customer_name=phone_number_to_call.contact_name))

            payload = {
                "voice": self.voice.value,
                "instrucciones": self.instrucciones.format(customer_name=phone_number_to_call.contact_name),
                "creatividadVoz": self.creatividadVoz
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f'https://{DOMAIN}/setSession',
                    json=payload,
                    headers=headers,

                )
            # Realiza la llamada
            print('Empezando llamada')
            call = self.client.calls.create(
                from_=PHONE_NUMBER_FROM,
                to=phone_number_to_call.phone_number,
                twiml=outbound_twiml,
                record=True,
                machine_detection=True,
                machine_detection_timeout=15,
                time_limit=self.callMaxDuration,
                timeout=15,

            )

            call_id = call.sid
            phone_number_to_call.call_id=call_id
            phone_number_to_call.update()
            #await self.log_call_sid(call_id)
            print(f"Llamada iniciada al número: {phone_number_to_call.phone_number}, SID: {call.sid}")

        # Espera a que esta llamada termine antes de continuar con la siguiente
            await self.esperar_a_que_finalice(call.sid,phone_number_to_call)
            await asyncio.sleep(5)  # Espera 5 segundos entre llamadas



    async def esperar_a_que_finalice(self, call_sid,call_db):
        """Espera asincrónicamente a que termine una llamada"""
        #from ..calls.models import Call
        while True:
            # Ejecuta la operación síncrona de Twilio en un hilo separado
            llamada = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.calls(call_sid).fetch()
            )

            print(f"Estado llamada {call_sid}: {llamada.status}")


            if llamada.status in ['completed', 'failed', 'busy', 'no-answer']:
                #llamada.transcriptions.create(inbound_track_label="Cliente",outbound_track_label="AI")
                #llamada.recordings.list()[0]..transcriptions.create()
                print(llamada.transcriptions)
                #await asyncio.sleep(30)
                #print(llamada._proxy.__dict__)
                #print(f"Llamada a dict: {llamada.__dict__}")
                #print(llamada.recordings.list()[0])
                call_db.call_id=llamada.sid
                call_db.status=llamada.status
                call_db.call_date=llamada.date_created
                call_db.call_duration=llamada.duration
                call_db.call_json_twilio=f'{llamada.__dict__}'
                call_db.update()
                break

            await asyncio.sleep(5)  # Consulta cada 5 segundos sin bloquear
    async def log_call_sid(self,call_sid):
        """Log the call SID."""
        print(f"Call started with SID: {call_sid}")






