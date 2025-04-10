import os
import json
import time

from fastapi.logger import logger

from app.agents.schemas import AgentResponse
from websocket_server.sessionManager import SessionManager
from fastapi import FastAPI, WebSocket, Request, Form
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import uvicorn
from authlib.integrations.starlette_client import OAuth
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import re
from app.agents.routers import router as agents_router
from app.calls.routers import router as calls_router
from app.users.routers import router as users_router
from app.users.auth import router as auth_router
from functionHandeler import functions

load_dotenv()

# Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
PHONE_NUMBER_FROM = os.getenv('TWILIO_NUMBER')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
raw_domain = os.getenv('DOMAIN', '')
DOMAIN = re.sub(r'(^\w+:|^)\/\/|\/+$', '', raw_domain)  # Strip protocols and trailing slashes from DOMAIN
PORT = int(os.getenv('PORT', 8765))
# app = FastAPI()


SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"


class Server:
    def __init__(self, PORT=8765, PROFILE_ID=1):
        self.app = FastAPI()
        self.PROFILE_ID = PROFILE_ID
        self.PROFILE_DATA = {}
        self.app.include_router(agents_router)
        self.app.include_router(calls_router)
        self.app.include_router(users_router)
        # self.app.include_router(auth_router, tags=["Authentication"])
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["*"]
        )
        self.app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY"))
        # with open(f"./Profiles/{self.PROFILE_ID}.json", mode="r", encoding="utf8") as data:
        #    self.PROFILE_DATA=json.load(data)
        # self.session_manager = SessionManager(VOICE=self.PROFILE_DATA["VOICE"],SYSTEM_MESSAGE=self.PROFILE_DATA["INSTRUCCTIONS"],CREATIVITY=0.6)
        self.session_manager = SessionManager(VOICE="alloy", SYSTEM_MESSAGE="Di hola", CREATIVITY=0.6)
        # self.session_manager=SessionManager()

        self.PORT = PORT
        self.CALL_ID = None

        @self.app.get('/', response_class=JSONResponse)
        async def index_page():
            return {"message": "Twilio Media Stream Server está corriendo!"}

        @self.app.websocket('/media-stream', )
        async def media_stream(websocket: WebSocket):
            # self.session_manager.CALL_ID=self.CALL_ID
            await self.session_manager.handle_media_stream(websocket)

        # from app.agents.schemas import AgentCreate
        @self.app.post('/setSession', response_class=JSONResponse, tags=["Agents"])
        # async def set_session(agent:AgentResponse):
        async def set_session(request: Request):
            # print(agent.dict())
            agent = await request.json()
            # print(f"Session: {agent}")
            # self.session_manager=SessionManager(VOICE=agent.voice,SYSTEM_MESSAGE=agent.instrucciones,CREATIVITY=agent.creatividadVoz)
            self.session_manager = SessionManager(VOICE=agent['voice'], SYSTEM_MESSAGE=agent['instrucciones'],
                                                  CREATIVITY=agent['creatividadVoz'])
            return {"message": "La sesion a sido actualizada"}

        @self.app.middleware("http")
        async def log_response_time(request: Request, call_next):
            start_time = time.time()
            response = await call_next(request)
            process_time = time.time() - start_time
            logger.info(f"Request: {request.url.path} completed in {process_time:.4f} seconds")
            return response

        @self.app.get("/tools", tags=["Agents"])
        def get_tools():
            print([f.schema.to_dict() for f in functions.get_all()])
            return JSONResponse([f.schema.to_dict() for f in functions.get_all()])

    def run(self):
        uvicorn.run(self.app, host="0.0.0.0", port=self.PORT)

    def assingCallid(self, callid):
        self.CALL_ID = callid


if __name__ == "__main__":
    server = Server(PROFILE_ID=2)
    server.run()
    # print("Hola: " + server.CALL_ID)
