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
#from app.db.session import Base
load_dotenv()
# Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
PHONE_NUMBER_FROM = os.getenv('TWILIO_NUMBER')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
raw_domain = os.getenv('DOMAIN', '')
DOMAIN = re.sub(r'(^\w+:|^)\/\/|\/+$', '', raw_domain)  # Strip protocols and trailing slashes from DOMAIN

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
    voice=Column(sqlalchemy.Enum(VoiceOptionsEnum),nullable=False,default=VoiceOptionsEnum.alloy)
    descripcion=Column(sqlalchemy.String(300),nullable=True)
    instrucciones=Column(sqlalchemy.String(65535),nullable=False)
    empezar_ia=Column(sqlalchemy.Boolean,nullable=False,default=True)
    velozidadVoz=Column(sqlalchemy.Float,default=1)
    creatividadVoz=Column(sqlalchemy.Float,default=0.6)
    silenceCloseCall=Column(sqlalchemy.Integer,default=30)
    callMaxDuration=Column(sqlalchemy.Integer)

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
        """Versión mejorada del método JSON"""
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

    async def make_call(self, numeros):
    #async def make_call(self,phone_number_to_call: str):
        """Make an outbound call."""
        #if not phone_number_to_call:
        #    raise ValueError("Please provide a phone number to call.")

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
            f'<Response><Connect><Stream url="wss://{DOMAIN}/media-stream" /></Connect></Response>'
        )
        for phone_number_to_call in numeros:
            # Realiza la llamada
            call = self.client.calls.create(
                from_=PHONE_NUMBER_FROM,
                to=phone_number_to_call,
                twiml=outbound_twiml,
                record=True,
                machine_detection=True,
                machine_detection_timeout=15,
                time_limit=self.callMaxDuration,
                timeout=self.silenceCloseCall,

            )

            call_id = call.sid
            #await self.log_call_sid(call_id)
            print(f"Llamada iniciada al número: {phone_number_to_call}, SID: {call.sid}")

        # Espera a que esta llamada termine antes de continuar con la siguiente
            self.esperar_a_que_finalice(call.sid)




    def esperar_a_que_finalice(self,call_sid):
        while True:
            llamada = self.client.calls(call_sid).fetch()
            print(f"Estado actual de la llamada {call_sid}: {llamada.status}")
            if llamada.status in ['completed', 'failed', 'busy', 'no-answer']:
                self.client.calls(call_sid).transcriptions.create()
                # La llamada ha finalizado (o no pudo completarse)
                break
            time.sleep(5)  # Espera 5 segundos antes de volver a verificar
    async def log_call_sid(self,call_sid):
        """Log the call SID."""
        print(f"Call started with SID: {call_sid}")





