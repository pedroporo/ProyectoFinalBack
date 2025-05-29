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
raw_domain = os.getenv('DOMAIN', '')
DOMAIN = re.sub(r'(^\w+:|^)\/\/|\/+$', '', raw_domain)  # Strip protocols and trailing slashes from DOMAIN
PORT = int(os.getenv('PORT', 8765))



SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"


class Server:
    def __init__(self, PORT=8765):
        self.app = FastAPI()
        self.app.include_router(api_router)
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
        self.session_manager: SessionManager=SessionManager()

        self.PORT = PORT
        self.CALL_ID = None

        @self.app.get('/', response_class=JSONResponse)
        async def index_page(request: Request):
            """
                            Para comprobar que el servicio esta disponible
                            \f
                            :agent_id: Id del agente.
                            """
            return {"message": "Twilio Media Stream Server está corriendo!"}

        @self.app.websocket('/media-stream')
        async def media_stream(websocket: WebSocket):
            """
                            Url para que twilio pueda conectarse a la api de gpt.
                            \f
                            """
            await self.session_manager.handle_media_stream(websocket)

        # from app.agents.schemas import AgentCreate
        @self.app.post('/setSession', response_class=JSONResponse, tags=["Agents"])
        async def set_session(request: Request):
            agent = await request.json()
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
            """
                            Puramente de pruebas, deberia desabilitarlo despues.
                            \f
                            :agent_id: Id del agente.
                            """
            return JSONResponse([f.schema.to_dict() for f in functions.get_all()])

        @self.app.on_event("startup")
        async def startup():
            """
                            Inicia la base de datos.
                            \f
                            :agent_id: Id del agente.
                            """
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

