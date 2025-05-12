import asyncio
import enum
import json
import os
import re

import httpx
import sqlalchemy
from dotenv import load_dotenv
from sqlalchemy import Column
from sqlalchemy import update, delete
from sqlalchemy.future import select
from sqlalchemy.orm.attributes import InstrumentedAttribute
# from main import call_id
from twilio.rest import Client

from app.db import Base
from app.db.context import get_current_db
from app.db.models import Database

# from websocket_server.server import Server
# from websocket_server.sessionManager import SessionManager

# from app.users.routers import get_user_db_session_class

# from app.users.routers import get_user_db

load_dotenv()
# Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_SERVICE_ID = os.getenv('TWILIO_SERVICE_ID')
PHONE_NUMBER_FROM = os.getenv('TWILIO_NUMBER')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
raw_domain = os.getenv('DOMAIN', '')
DOMAIN = re.sub(r'(^\w+:|^)\/\/|\/+$', '', raw_domain)
PORT = int(os.getenv('PORT', 8765))


# get_db_session_class = get_user_db_session_class()


class VoiceOptionsEnum(enum.Enum):
    alloy = 'alloy'
    ash = 'ash'
    ballad = 'ballad'
    coral = 'coral'
    echo = 'echo'
    sage = 'sage'
    shimmer = 'shimmer'
    verse = 'verse'


class Agent(Base):
    __tablename__ = 'agents'

    id = Column(sqlalchemy.Integer, primary_key=True, index=True)
    name = Column(sqlalchemy.String(20), nullable=False)
    voice = Column(sqlalchemy.Enum(VoiceOptionsEnum), nullable=False, default=VoiceOptionsEnum.alloy,
                   server_default=VoiceOptionsEnum.alloy.value)
    descripcion = Column(sqlalchemy.String(300), nullable=True)
    instrucciones = Column(sqlalchemy.Text, nullable=False)
    empezar_ia = Column(sqlalchemy.Boolean, nullable=False, default=True)
    velozidadVoz = Column(sqlalchemy.Float, default=1)
    creatividadVoz = Column(sqlalchemy.Float, default=0.6)
    silenceCloseCall = Column(sqlalchemy.Integer, default=30)
    callMaxDuration = Column(sqlalchemy.Integer)
    phone_number = Column(sqlalchemy.String(20), nullable=True)

    # calls= relationship("Call", back_populates="agent", cascade="all, delete-orphan")
    async def update(self):
        # s = get_db_session()
        db = get_current_db()
        async with db.get_db_session_class() as s:
            mapped_values = {}
            for item in Agent.__dict__.items():
                field_name = item[0]
                field_type = item[1]
                is_column = isinstance(field_type, InstrumentedAttribute)
                if is_column:
                    mapped_values[field_name] = getattr(self, field_name)

            # s.query(Call).filter(Call.call_id == self.call_id).update(mapped_values)
            await s.execute(update(Agent).where(Agent.id == self.id).values(**mapped_values))
            await s.commit()

    async def delete(self):
        # s = get_db_session()
        db = get_current_db()
        async with db.get_db_session_class() as s:
            await s.execute(delete(Agent).where(Agent.id == self.id))
            await s.commit()

    async def create(self):
        # async def create(self, db):
        # s = get_db_session()
        db = get_current_db()
        async with db.get_db_session_class() as s:
            # await s.add(self)
            s.add(self)
            await s.commit()
            await s.refresh(self)

    async def get(self):
        db = get_current_db()
        async with db.get_db_session_class() as s:
            result = await s.execute(select(Agent).where(Agent.id == self.id))
            return result.scalar()

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
            'callMaxDuration': self.callMaxDuration,
            'phone_number': self.phone_number,
        }

    def toJSON(self):
        return json.dumps(self.to_dict(), indent=4)

    # if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and PHONE_NUMBER_FROM and OPENAI_API_KEY):
    #     raise ValueError('Missing Twilio and/or OpenAI environment variables. Please set them in the .env file.')

    # Initialize Twilio client

    async def check_number_allowed(self, to):
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

    async def make_call(self, db: Database):
        # async def make_call(self,phone_number_to_call: str):
        """Make an outbound call."""
        # if not phone_number_to_call:
        #    raise ValueError("Please provide a phone number to call.")
        from ..calls.models import Call
        # db = await anext(get_db_session())
        # db=get_db_session()

        # result = await db.execute(select(Call).where(Call.agent_id == self.id and Call.status == "ready"))
        async with db.get_db_session_class() as s:
            # print(s)
            result = await s.execute(
                select(Call).where(sqlalchemy.and_(Call.agent_id == self.id, Call.status == "ready")))
            numeros = result.scalars().all()
        # print(numeros)

        # print(payload)
        headers = {
            'Content-Type': 'application/json',
        }

        # response = requests.request("POST", f'https://{DOMAIN}/setSession/',headers=headers, data=payload,json=payload,allow_redirects=True)

        # response = requests.request("POST", f'https://{DOMAIN}/setSession/', headers=headers, json=self.to_dict(),allow_redirects=True,verify=False)
        # print(response.text)
        # Server.session_manager=SessionManager(VOICE=self.voice.value,SYSTEM_MESSAGE=self.instrucciones,CREATIVITY=self.creatividadVoz)
        # is_allowed = await self.check_number_allowed(phone_number_to_call)
        # if not is_allowed:
        #    raise ValueError(
        #        f"The number {phone_number_to_call} is not recognized as a valid outgoing number or caller ID.")

        # Ensure compliance with applicable laws and regulations
        # All of the rules of TCPA apply even if a call is made by AI.
        # Do your own diligence for compliance.

        self.client = Client(self.user.config_user['credentials']['TWILIO_ACCOUNT_SID'],
                             self.user.config_user['credentials']['TWILIO_AUTH_TOKEN'])
        outbound_twiml = (
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<Response><Connect><Stream url="wss://{DOMAIN}/media-stream" /> </Connect><Pause length="{self.silenceCloseCall}"/><Hangup/></Response>'
        )
        for phone_number_to_call in numeros:
            # test=str(self.instrucciones).format(customer_name=phone_number_to_call.contact_name)
            # print(self.instrucciones.format(customer_name=phone_number_to_call.contact_name))

            payload = {
                "voice": self.voice.value,
                "instrucciones": self.instrucciones.format(customer_name=phone_number_to_call.contact_name),
                "creatividadVoz": self.creatividadVoz,
                "googleCreds": self.googleCreds,
                "user": self.user.toJSON(),
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f'https://{DOMAIN}/setSession',
                    json=payload,
                    headers=headers,

                )
            # Realiza la llamada
            # print('Empezando llamada')
            call = self.client.calls.create(
                from_=self.phone_number|  self.user.config_user['credentials']['TWILIO_NUMBER'],
                to=phone_number_to_call.phone_number,
                twiml=outbound_twiml,
                record=True,
                machine_detection=True,
                machine_detection_timeout=15,
                time_limit=self.callMaxDuration,
                timeout=15,

            )

            call_id = call.sid
            phone_number_to_call.call_id = call_id
            await phone_number_to_call.update()
            # await self.log_call_sid(call_id)
            # print(f"Llamada iniciada al número: {phone_number_to_call.phone_number}, SID: {call.sid}")

            # Espera a que esta llamada termine antes de continuar con la siguiente
            await self.esperar_a_que_finalice(call.sid, phone_number_to_call)
            await asyncio.sleep(5)  # Espera 5 segundos entre llamadas
        return {"message": f'Se han llamado a {len(numeros)} numeros telefonicos'}

    async def esperar_a_que_finalice(self, call_sid, call_db):
        """Espera asincrónicamente a que termine una llamada"""
        # from ..calls.models import Call
        while True:
            # Ejecuta la operación síncrona de Twilio en un hilo separado
            llamada = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.calls(call_sid).fetch()
            )

            # print(f"Estado llamada {call_sid}: {llamada.status}")

            if llamada.status in ['completed', 'failed', 'busy', 'no-answer']:
                # llamada.transcriptions.create(inbound_track_label="Cliente",outbound_track_label="AI")
                # llamada.recordings.list()[0]..transcriptions.create()
                # print(llamada.transcriptions.__dict__)
                # await asyncio.sleep(30)
                # print(llamada._proxy.__dict__)
                # print(f"Llamada a dict: {llamada.__dict__}")
                # print(llamada.recordings.list()[0])

                call_db.call_id = llamada.sid
                call_db.status = llamada.status
                call_db.call_date = llamada.date_created
                call_db.call_duration = llamada.duration
                call_db.call_json_twilio = f'{llamada.__dict__}'
                await call_db.update()
                if llamada.status == 'completed':
                    # await asyncio.sleep(5)
                    recordings = self.client.recordings.list(call_sid=llamada.sid, page_size=1)
                    # transcriptions = self.client.intelligence.v2.transcripts.list(source_sid=recordings[0].sid,
                    #                                                               page_size=1)
                    transcript = None
                    try:
                        transcript = self.client.intelligence.v2.transcripts.create(
                            channel={
                                "media_properties": {"source_sid": recordings[0].sid},
                                "participants": [
                                    {
                                        "user_id": "id1",
                                        "channel_participant": 1,
                                        # "media_participant_id": llamada.to,
                                        "full_name": call_db.contact_name,
                                        "role": "Cliente",
                                    },
                                    {
                                        "user_id": "id2",
                                        "channel_participant": 2,
                                        # "media_participant_id": PHONE_NUMBER_FROM,
                                        "full_name": "IA",
                                        "role": "IA",
                                    },
                                ],
                            },
                            service_sid=TWILIO_SERVICE_ID
                        )
                    except Exception as e:
                        print(f"Error al crear la transcripción: {e}")

                    await self.esperar_a_transcript(transcript_sid=transcript.sid, call_sid=llamada.sid)

                    # print(transcriptions[0].sentences.list(redacted=False))
                    # recording_url = self.get_recording_url(llamada.sid)
                    # transcription = await self.transcribe_audio(recording_url)
                    # await self.save_transcription(text=transcription, call_sid=llamada.sid)
                    # print(f"Transcripción: {transcription}")
                break

            await asyncio.sleep(5)  # Consulta cada 5 segundos sin bloquear

    async def log_call_sid(self, call_sid):
        """Log the call SID."""
        print(f"Call started with SID: {call_sid}")

    def get_recording_url(self, call_sid: str) -> str:
        recordings = self.client.recordings.list(call_sid=call_sid, page_size=1)
        if not recordings:
            raise Exception("No se encontraron grabaciones para esta llamada")
        return f"https://api.twilio.com{recordings[0].uri.replace('.json', '')}"

    async def transcribe_audio(self, audio_url: str) -> str:
        import requests
        from openai import OpenAI
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        # Descargar el archivo de audio desde Twilio
        # self.client.request('GET', uri=audio_url)

        try:
            response = requests.get(url=audio_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN), timeout=10)
            response.raise_for_status()  # Lanza error para códigos 4xx/5xx

        except requests.HTTPError as err:
            error_msg = f"Error HTTP {err.response.status_code}: {err.response.text}"
            print(error_msg)
            raise Exception(error_msg)

        except requests.Timeout:
            raise Exception("Timeout al descargar el audio")

        except Exception as err:
            raise Exception(f"Error inesperado: {str(err)}")

        if response.status_code != 200:
            raise Exception("Error al descargar el archivo de audio")

        # Guardar el archivo localmente
        with open("temp_audio.wav", "wb") as f:
            f.write(response.content)
            f.close()

        # Enviar a la API de OpenAI para transcripción
        with open("temp_audio.wav", "rb") as audio_file:
            transcription = openai_client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-1",
                response_format="text",

            )
            audio_file.close()

        os.remove("temp_audio.wav")
        return transcription

    async def esperar_a_transcript(self, transcript_sid, call_sid):
        while True:
            transcript = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.intelligence.v2.transcripts(transcript_sid).fetch()
            )
            # print(f"Estado llamada {transcript_sid}: {transcript.status}")
            if transcript.status == 'completed':
                texto = '\n'.join(f'{"IA" if x.media_channel == 2 else "Usuario"}: {str(x.transcript)}' for x in
                                  transcript.sentences.list(redacted=False))
                await self.save_transcription(text=texto, call_sid=call_sid)
                transcript.delete()
                # print(f"Transcripción: {texto}")
                break
            await asyncio.sleep(5)

    async def save_transcription(self, text: str, call_sid):

        from app.calls.models import Transcription
        transcription = Transcription(
            call_id=call_sid,
            content=text
        )
        await transcription.create()
