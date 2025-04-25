from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.db.context import set_current_db
from app.db.settings import local_db
from app.users.models import User
from app.users.routers import validate_user_request


# test = 'Authorization'


class DBMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            public_paths = ["/setSession", "/media-stream", "/tools", "/",
                            "/api/users/login/google",
                            "/api/users/auth/google", "/docs",
                            "/openapi.json"]  # Añade aquí las rutas que no requieren auth
            if request.url.path in public_paths:
                return await call_next(request)
            # print(f'Recuest: {await request.json()}')
            # print(f'Recuesta cookie: {request.cookies.get("access_token")}')
            user: User = await validate_user_request(token=request.cookies.get("access_token"))
            # print(f'User: {user.to_dict()}')
            if user:
                db = await user.get_user_database()
                # print(f'Db in middleware: {db.to_dict()}')
                set_current_db(db)
            else:
                set_current_db(local_db)
        except HTTPException as e:
            print(f"Error en HTTPException: {e}")
            set_current_db(local_db)
            raise e
        except Exception as e:
            print(f"Error en DBMiddleware: {e}")
            # set_current_db(local_db)
            # raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")

        response = await call_next(request)
        # print(f'Respusta del DBMiddleWare: {response.}')
        return response
