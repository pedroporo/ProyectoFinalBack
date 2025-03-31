import os

from sessionManager import SessionManager
from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocketDisconnect
from twilio.rest import Client
import websockets
from dotenv import load_dotenv
import uvicorn
import re

load_dotenv()

# Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
PHONE_NUMBER_FROM = os.getenv('TWILIO_NUMBER')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
raw_domain = os.getenv('DOMAIN', '')
DOMAIN = re.sub(r'(^\w+:|^)\/\/|\/+$', '', raw_domain) # Strip protocols and trailing slashes from DOMAIN
call_id=None
PORT = int(os.getenv('PORT', 8765))
SYSTEM_MESSAGE = (
    "Eres un asistente de IA servicial y jovial, a quien le encanta charlar sobre cualquier tema que interese al usuario y siempre está dispuesto a ofrecerle información. Te encantan los chistes de papá, los chistes de búhos y los rickrolls, sutilmente. Mantén siempre una actitud positiva, pero incluye un chiste cuando sea necesario. "
)
VOICE = 'alloy'
LOG_EVENT_TYPES = [
    'error', 'response.content.done', 'rate_limits.updated', 'response.done',
    'input_audio_buffer.committed', 'input_audio_buffer.speech_stopped',
    'input_audio_buffer.speech_started', 'session.created'
]
SHOW_TIMING_MATH = False
app = FastAPI()

if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and PHONE_NUMBER_FROM and OPENAI_API_KEY):
    raise ValueError('Missing Twilio and/or OpenAI environment variables. Please set them in the .env file.')

# Initialize Twilio client
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


class Server:
    def __init__(self):
        self.app = FastAPI()
        self.session_manager = SessionManager()

        @self.app.get('/', response_class=JSONResponse)
        async def index_page():
            return {"message": "Twilio Media Stream Server está corriendo!"}

        @self.app.websocket('/media-stream')
        async def media_stream(websocket: WebSocket):
            await self.session_manager.handle_media_stream(websocket)

    def run(self):
        uvicorn.run(self.app, host="0.0.0.0", port=PORT)
if __name__ == "__main__":
    server = Server()
    server.run()