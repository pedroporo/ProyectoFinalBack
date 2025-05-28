from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.db.context import set_current_db
from app.db.settings import local_db
from app.users.models import User
from app.users.routers import validate_user_request


# test = 'Authorization'


class DBMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            #print(f'Path: {request.url.path}')
            public_paths = ["/setSession", "/media-stream", "/tools", "/",
                            "/api/users/login/google",
                            "/api/users/auth/google", "/docs",
                            "/openapi.json", "/api/users/login",
                            "/api/users/register"]  # Añade aquí las rutas que no requieren auth
            if request.url.path in public_paths:
                return await call_next(request)
            token=request.cookies.get("access_token")
            if not token:
                token=request.headers.get('Authorization').split(" ")[1]
            user: User = await validate_user_request(token=token)
            if user:
                db = await user.get_user_database()
                set_current_db(db)
            else:
                set_current_db(local_db)
        except HTTPException as e:
            print(f"Error en HTTPException: {e.__dict__}")
            set_current_db(local_db)
            return JSONResponse(content=e.detail,status_code=e.status_code)
            #raise e
        except Exception as e:
            print(f"Error en DBMiddleware: {e.__dict__}")
            # set_current_db(local_db)
            # raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")
            #return JSONResponse(content=e.__dict__, status_code=500)
            #raise e

        response = await call_next(request)
        #print(f'Respusta del DBMiddleWare: {response.__dict__}')
        return response
