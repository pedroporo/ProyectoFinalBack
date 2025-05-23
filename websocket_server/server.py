import os
import re
import time

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, Request
from fastapi.logger import logger
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app import router as api_router
from app.db.middleware import DBMiddleware
from websocket_server.functionHandeler import functions
from websocket_server.sessionManager import SessionManager

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
    def __init__(self, PORT=8765):
        self.app = FastAPI()
        self.app.include_router(api_router)
        # self.app.include_router(auth_router, tags=["Authentication"])
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["*"]
        )
        self.app.add_middleware(DBMiddleware)
        self.app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY"))
        # with open(f"./Profiles/{self.PROFILE_ID}.json", mode="r", encoding="utf8") as data:
        #    self.PROFILE_DATA=json.load(data)
        # self.session_manager = SessionManager(VOICE=self.PROFILE_DATA["VOICE"],SYSTEM_MESSAGE=self.PROFILE_DATA["INSTRUCCTIONS"],CREATIVITY=0.6)
        self.session_manager: SessionManager = None
        # self.session_manager=SessionManager()

        self.PORT = PORT
        self.CALL_ID = None

        @self.app.get('/', response_class=JSONResponse)
        async def index_page(request: Request):
            return {"message": "Twilio Media Stream Server está corriendo!"}

        @self.app.websocket('/media-stream')
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
            self.session_manager.setSession(VOICE=agent['voice'], SYSTEM_MESSAGE=agent['instrucciones'],
                                                  CREATIVITY=agent['creatividadVoz'], GOOGLE_CREDS=agent['googleCreds'],
                                                  USER=agent['user'],CALL=agent['call'])
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
            # print([f.schema.to_dict() for f in functions.get_all()])
            return JSONResponse([f.schema.to_dict() for f in functions.get_all()])

        @self.app.on_event("startup")
        async def startup():
            # Inicializa la base de datos al iniciar la aplicación
            from app.db.settings import local_db
            await local_db.init_models()

    def run(self):
        uvicorn.run(self.app, host="0.0.0.0", port=self.PORT)

    def assingCallid(self, callid):
        self.CALL_ID = callid


if __name__ == "__main__":
    server = Server()
    server.run()
    # print("Hola: " + server.CALL_ID)
