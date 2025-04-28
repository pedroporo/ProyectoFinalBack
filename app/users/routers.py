import logging as logger
import os
import re
import uuid
from datetime import datetime, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

import jwt
import requests
from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, status, HTTPException, Request, Cookie
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.settings import local_db
from .models import User as UserModel, GoogleCredential
from .schemas import User, UserInDB, Token, TokenData, UserCreate
from ..db.models import Database

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter(prefix="/users", tags=["Users"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 4320

oauth = OAuth()
oauth.register(
    name="auth_demo",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    authorize_url="https://accounts.google.com/o/oauth2/auth",
    authorize_params=None,
    access_token_url="https://accounts.google.com/o/oauth2/token",
    access_token_params=None,
    refresh_token_url="https://accounts.google.com/o/oauth2/token",
    authorize_state=os.getenv("SECRET_KEY"),
    redirect_uri=os.getenv("REDIRECT_URL"),

    jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
    client_kwargs={
        "scope": "openid profile email https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/calendar.readonly https://www.googleapis.com/auth/calendar.events https://www.googleapis.com/auth/calendar.events.readonly"},
)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


async def get_user(db, username: str):
    # result = await db.execute(select(User).where(User.username == username))
    user = await UserModel(username=username).get()
    if user:
        return UserInDB(**user.to_dict())
    return None


async def authenticate_user(username: str, password: str):
    # user = await get_user(db, username)
    if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', username):
        user = await UserModel(email=username).getByGmail()
    else:
        user = await UserModel(username=username).get()
    print(f'User atuh: {user}')
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(ZoneInfo("Europe/Madrid")) + expires_delta
    else:
        expire = datetime.now(ZoneInfo("Europe/Madrid")) + timedelta(days=30)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)],
                           db: AsyncSession = Depends(local_db.get_db_session)):
    # print(token)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # username = payload.get("sub")
        print(f'Get current user email: {payload.get("email")}')
        username: UserModel = await UserModel(email=payload.get("email")).getByGmail()
        print(f'User: {username}')
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username.username)
    except InvalidTokenError:
        raise credentials_exception
    # user = await get_user(db, username=token_data.username)
    user = await UserModel(username=token_data.username).get()
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
        current_user: Annotated[UserModel, Depends(get_current_user)],
        db: AsyncSession = Depends(local_db.get_db_session)
) -> UserModel:
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def validate_user_request(token: str = Cookie(None)):
    session_details = await get_current_user(token)

    return session_details


async def log_user(user_id, user_email, user_name, user_pic, first_logged_in, last_accessed):
    usuario = None
    try:
        usuario: UserModel = await UserModel(username=user_name).get()
        # print(f'Usuario get: {usuario.toJSON()}')
        if usuario != None:
            await UserModel(id=usuario.id, username=user_name, email=user_email, password=usuario.password,
                            role=usuario.role,
                            avatar=user_pic, google_id=user_id, config_user=usuario.config_user).update()
        else:
            new_user = UserModel(username=user_name, email=user_email, avatar=user_pic, google_id=user_id,
                                 disabled=False)
            # print(f'Usuario en el router: {new_user.toJSON()}')
            usuario = await new_user.create()
            # print(f'Usuario despues del create: {usuario.toJSON()}')


    except Exception as e:
        print("Error while updating or creating user: ", e)
    finally:
        if usuario != None:
            logger.info("User created or updated")


async def get_google_creds(
        user: UserModel = Depends(get_current_active_user),
        db: AsyncSession = Depends(local_db.get_db_session)
):
    # print(user.google_id)
    creds: GoogleCredential = await GoogleCredential().getFromUser(user_id=user.google_id)
    # print(creds.to_dict())
    if not creds:
        raise HTTPException(404, "Credenciales no encontradas para el usuario")
    margen_de_seguridad = timedelta(minutes=5)
    if creds.expires_at < datetime.now(ZoneInfo("Europe/Madrid")) + margen_de_seguridad:
        if not creds.refresh_token:
            # response = RedirectResponse(f'{os.getenv("REDIRECT_URL")}/api/users/login/google')
            # return response
            raise HTTPException(403, "Reautenticación requerida con Google (no refresh token)")
        try:
            # print('Refrescando token')
            token_data = await refresh_google_token(creds.refresh_token)
            creds.access_token = token_data["access_token"]
            creds.expires_at = datetime.now(ZoneInfo("Europe/Madrid")) + timedelta(seconds=token_data["expires_in"])
            await creds.update()
        except Exception as e:
            raise HTTPException(500, f"Error al refrescar el token: {e}")

    return creds


async def refresh_google_token(refresh_token: str):
    """
    Refresca el access token de Google utilizando el refresh token.
    """
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    response = requests.post(GOOGLE_TOKEN_URL, data=data)
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()


async def get_user_db(current_user: User = Depends(get_current_active_user)):
    """
    Retorna la classe de la base de datos configurada
    """
    return await current_user.get_user_database()


async def get_user_db_session(db: Database = Depends(get_user_db)):
    """
    Retorna la sesion normal de la base de datos configurada del usuario
    """
    async with db.get_db_session() as s:
        return s


# from contextlib import asynccontextmanager
#
#
# @asynccontextmanager
async def get_user_db_session_class(db: Database = Depends(get_user_db)):
    """
    Retorna la sesion para las clases de la base de datos configurada del usuario
    """
    async with db.get_db_session_class() as s:
        return s


# async def log_token(access_token, user_email, session_id):
#     try:
#         connection = mysql.connector.connect(host=host, database=database, user=user, password=password)
#
#         if connection.is_connected():
#             cursor = connection.cursor()
#
#             # SQL query to insert data
#             sql_query = """INSERT INTO issued_tokens (token, email_id, session_id) VALUES (%s,%s,%s)"""
#             # Execute the SQL query
#             cursor.execute(sql_query, (access_token, user_email, session_id))
#
#             # Commit changes
#             connection.commit()
#
#     except Exception as e:
#         print("Error while connecting to MySQL", e)


@router.get("/login/google")
async def login(request: Request, db: AsyncSession = Depends(local_db.get_db_session)):
    request.session.clear()
    referer = request.headers.get("referer")
    frontend_url = os.getenv("FRONTEND_URL")
    redirect_url = os.getenv("REDIRECT_URL")
    request.session["login_redirect"] = frontend_url
    return await oauth.auth_demo.authorize_redirect(request, redirect_url, prompt="consent", access_type="offline")


@router.get("/auth/google")
async def auth(request: Request, db: AsyncSession = Depends(local_db.get_db_session)):
    try:
        token = await oauth.auth_demo.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Google authentication failed.")

    try:
        user_info_endpoint = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {"Authorization": f'Bearer {token["access_token"]}'}
        google_response = requests.get(user_info_endpoint, headers=headers)
        user_info = google_response.json()
    except Exception as e:
        raise HTTPException(status_code=401, detail="Google authentication failed.")

    user = token.get("userinfo")
    expires_in = token.get("expires_in")
    user_id = user.get("sub")
    iss = user.get("iss")
    user_email = user.get("email")
    first_logged_in = datetime.now(ZoneInfo("Europe/Madrid"))
    last_accessed = datetime.now(ZoneInfo("Europe/Madrid"))

    user_name = user_info.get("name")
    user_pic = user_info.get("picture")

    if iss not in ["https://accounts.google.com", "accounts.google.com"]:
        raise HTTPException(status_code=401, detail="Google authentication failed.")

    if user_id is None:
        raise HTTPException(status_code=401, detail="Google authentication failed.")

    # Create JWT token
    access_token_expires = timedelta(seconds=expires_in)
    access_token = create_access_token(data={"sub": user_id, "email": user_email}, expires_delta=access_token_expires)

    session_id = str(uuid.uuid4())
    await log_user(user_id, user_email, user_name, user_pic, first_logged_in, last_accessed)
    # log_token(access_token, user_email, session_id)

    redirect_url = request.session.pop("login_redirect", "")
    response = RedirectResponse(redirect_url)
    expires_at = datetime.now(ZoneInfo("Europe/Madrid")) + timedelta(seconds=token["expires_in"])
    print(f'Access Token: {access_token}')
    print(f'Access Token Google: ' + token['access_token'])
    print(f'Token Google: {token}')
    print(f'Time when expire: {expires_at}')
    print(f'Time Now: {datetime.now(ZoneInfo("Europe/Madrid"))}')
    print(f'Time expire in: {timedelta(seconds=token["expires_in"])}')
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,  # Ensure you're using HTTPS
        samesite="strict",  # Set the SameSite attribute to None
    )
    if await GoogleCredential(user_id=user_id).get():
        await GoogleCredential(
            user_id=user_id,
            access_token=token['access_token'],
            refresh_token=token.get('refresh_token'),
            expires_at=expires_at
        ).update()
    else:
        await GoogleCredential(
            user_id=user_id,
            access_token=token['access_token'],
            refresh_token=token.get('refresh_token'),
            expires_at=expires_at
        ).create()
    return response


@router.get("/testDB")
# async def test(
#         creds: GoogleCredential = Depends(get_google_creds)):
#     from googleapiclient.discovery import build
#     from google.oauth2.credentials import Credentials
#     creds2 = Credentials(token=creds.access_token)
#     print(creds.to_dict())
#     service = build('calendar', 'v3', credentials=creds2)
#     print(service.calendarList().list().execute())
#     return service.calendarList().list().execute()
async def test(
        current_user: Annotated[UserModel, Depends(get_current_active_user)],
        db: AsyncSession = Depends(local_db.get_db_session)
):
    # database = await current_user.get_user_database()
    return JSONResponse(content=current_user.to_dict(), status_code=200)
    # return current_user.toJSON()


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    response = JSONResponse(content={"message": "Logged out successfully."})
    response.delete_cookie("access_token")
    return response


@router.post("/login", tags=["Login"])
async def login_for_access_token(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: AsyncSession = Depends(local_db.get_db_session)
) -> Token:
    user: UserModel = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(days=30)
    access_token = create_access_token(
        data={"sub": user.username, "email": user.email}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@router.post("/register", tags=["Login"])
async def register(user: UserCreate):
    print(user)
    if (usuario := await UserModel(username=user.username).get()):
        return JSONResponse(content={"message": "User alredy exists."}, status_code=409)
    new_user: UserModel = await UserModel(username=user.username, password=get_password_hash(user.password),
                                          email=user.email).create()
    access_token_expires = timedelta(days=30)
    access_token = create_access_token(
        data={"sub": new_user.username, "email": new_user.email}, expires_delta=access_token_expires
    )
    token = Token(access_token=access_token, token_type="bearer")
    print(f'Token: {token}')
    response = JSONResponse(content=token.dict(), status_code=201)
    response.set_cookie(
        key="access_token",
        value=token.access_token,
        httponly=True,
        secure=True,  # Ensure you're using HTTPS
        samesite="strict",  # Set the SameSite attribute to None
    )
    return response


@router.get("/me", response_model=User)
async def read_users_me(
        current_user: Annotated[UserModel, Depends(get_current_active_user)],
        db: AsyncSession = Depends(local_db.get_db_session)
):
    return JSONResponse(content=current_user.to_dict(), status_code=200)
    # return current_user.toJSON()


@router.patch("/me", response_model=User)
async def update_user(current_user: Annotated[UserModel, Depends(get_current_active_user)], user: UserCreate,
                      db: AsyncSession = Depends(local_db.get_db_session)):
    try:
        # config = user.config_user
        # user.config_user = ''
        current_user.username = user.username
        current_user.email = user.email
        current_user.avatar = current_user.avatar if user.avatar == None else user.avatar
        current_user.config_user = current_user.config_user if user.config_user == None else user.config_user
        # new_user = UserModel(id=current_user.id, username=user.username, email=user.email,
        #                      avatar=user.avatar, config_user=user.config_user)
        # new_user = UserModel(id=current_user.id, **user.dict())
        # new_user.config_user = json.dumps(config)
        await current_user.update()
        return JSONResponse(content=current_user.to_dict(), status_code=200)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/force-refresh-google-token")
async def force_refresh_google_token(
        current_user: Annotated[UserModel, Depends(get_current_active_user)]
):
    print('Entro en la funcion')
    creds: GoogleCredential = await GoogleCredential().getFromUser(user_id=current_user.google_id)
    if not creds:
        raise HTTPException(404, "Credenciales de Google no encontradas para el usuario.")

    if not creds.refresh_token:
        raise HTTPException(403, "No hay refresh_token guardado. Reautenticación requerida.")

    try:
        token_data = await refresh_google_token(creds.refresh_token)
        new_access_token = token_data["access_token"]
        expires_in = token_data["expires_in"]
        new_expiration = datetime.now(ZoneInfo("Europe/Madrid")) + timedelta(seconds=expires_in)

        creds.access_token = new_access_token
        creds.expires_at = new_expiration
        await creds.update()
        return {
            "message": "Token refrescado correctamente",
            "access_token": new_access_token,
            "expires_at": new_expiration
        }
    except Exception as e:
        raise HTTPException(500, f"Error al refrescar el token: {e}")
# Old
# @router.post("/calls/", response_model=CallResponse)
# async def create_call(call: CallCreate, db: AsyncSession = Depends(get_db_session)):
#     try:
#         new_call = Call(**call.dict())
#         await new_call.create()
#         # db.add(new_agent)
#         # await db.commit()
#         # await db.refresh(new_agent)
#         return new_call.to_dict()
#     except Exception as e:
#         await db.rollback()
#         raise HTTPException(status_code=400, detail=str(e))
#
#
# @router.get("/calls/{call_id}", response_model=CallResponse)
# async def get_call(call_id: int, db: AsyncSession = Depends(get_db_session)):
#     result = await db.execute(select(Call).where(Call.id == call_id))
#     call = result.scalar()
#     if not call:
#         raise HTTPException(status_code=404, detail="Llamada no encontrado")
#     return JSONResponse(content=call.to_dict(), status_code=200)
#
#
# @router.put("/calls/{call_id}", response_model=CallResponse)
# async def update_call(call_id: int, agent: CallCreate, db: AsyncSession = Depends(get_db_session)):
#     try:
#         new_call = Call(id=call_id, **agent.dict())
#         await new_call.update()
#         return JSONResponse(content={"message": "La llamada a sido actualizada"}, status_code=200)
#     except Exception as e:
#         await db.rollback()
#         raise HTTPException(status_code=400, detail=str(e))
#
#
# @router.delete("/calls/{call_id}", response_model=CallResponse)
# async def del_call(call_id: int, db: AsyncSession = Depends(get_db_session)):
#     result = await db.execute(select(Call).where(Call.id == call_id))
#     call = result.scalar()
#     call.delete()
#     if not call:
#         raise HTTPException(status_code=404, detail="Llamada no encontrado")
#     return JSONResponse(content={"message": "La llamada a sido eliminada"}, status_code=200)
#
#
# @router.get("/calls/{agent_id}", response_model=None)
# async def get_agents_call(agent_id: int, db: AsyncSession = Depends(get_db_session)):
#     result = await db.execute(select(Call).where(Call.agent_id == agent_id))
#     llamadas = result.scalars().all()
#     # print({'agents': [agent.to_dict() for agent in agents]})
#     if not llamadas:
#         raise HTTPException(status_code=404, detail="Llamadas no encontrado")
#     return JSONResponse(content={'calls': [llamada.to_dict() for llamada in llamadas]}, status_code=200)
