import os
import json
from websocket_server.sessionManager import SessionManager
from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import uvicorn
import re
from app.agents.routers import app as agents_router

load_dotenv()

# Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
PHONE_NUMBER_FROM = os.getenv('TWILIO_NUMBER')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
raw_domain = os.getenv('DOMAIN', '')
DOMAIN = re.sub(r'(^\w+:|^)\/\/|\/+$', '', raw_domain) # Strip protocols and trailing slashes from DOMAIN
PORT = int(os.getenv('PORT', 8765))
SYSTEM_MESSAGE = (
    "Eres un asistente de IA servicial y jovial, a quien le encanta charlar sobre cualquier tema que interese al usuario y siempre está dispuesto a ofrecerle información. Te encantan los chistes de papá, los chistes de búhos y los rickrolls, sutilmente. Mantén siempre una actitud positiva, pero incluye un chiste cuando sea necesario. "
)
VOICE = 'alloy'
app = FastAPI()


class Server:
    def __init__(self,PORT=8765,PROFILE_ID=1):
        self.app = FastAPI()
        self.PROFILE_ID = PROFILE_ID
        self.PROFILE_DATA={}
        self.app.include_router(agents_router)
        with open(f"../Profiles/{self.PROFILE_ID}.json", mode="r", encoding="utf8") as data:
            self.PROFILE_DATA=json.load(data)
        self.session_manager = SessionManager(VOICE=self.PROFILE_DATA["VOICE"],SYSTEM_MESSAGE=self.PROFILE_DATA["INSTRUCCTIONS"])
        self.PORT=PORT
        self.CALL_ID=None
        @self.app.get('/', response_class=JSONResponse)
        async def index_page():
            return {"message": "Twilio Media Stream Server está corriendo!"}
        @self.app.websocket('/media-stream')
        async def media_stream(websocket: WebSocket):
            await self.session_manager.handle_media_stream(websocket)
        @self.app.post('/events')
        async def event_manager(eventos):
            print("Hola mundo"+eventos)

    def run(self):
        uvicorn.run(self.app, host="0.0.0.0", port=self.PORT)

    def assingCallid(self,callid):
        self.CALL_ID = callid


if __name__ == "__main__":
    server = Server(PROFILE_ID=2)
    server.run()
    #print("Hola: " + server.CALL_ID)