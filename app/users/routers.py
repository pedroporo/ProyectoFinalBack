from fastapi import APIRouter, Depends, status, HTTPException, FastAPI, Request, Cookie
from fastapi.encoders import jsonable_encoder
from fastapi.security import HTTPBearer, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Annotated
from datetime import datetime, timedelta, timezone
from jwt.exceptions import InvalidTokenError
import os
import uuid
import traceback
import jwt
from sqlalchemy.future import select
from fastapi.responses import JSONResponse, RedirectResponse
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from .schemas import User, UserInDB, Token, TokenData
from .models import User as UserModel, GoogleCredential
from app.db.session import get_db_session
import requests
from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv
import logging as logger

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
    refresh_token_url=None,
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


async def authenticate_user(db, username: str, password: str):
    user = await get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: AsyncSession = Depends(get_db_session)):
    print(token)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # username = payload.get("sub")
        username = await UserModel(google_id=payload.get("sub")).getByGId()
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username.username)
    except InvalidTokenError:
        raise credentials_exception
    user = await get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
        current_user: Annotated[User, Depends(get_current_user)], db: AsyncSession = Depends(get_db_session)
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def validate_user_request(token: str = Cookie(None)):
    session_details = get_current_user(token)

    return session_details


async def log_user(user_id, user_email, user_name, user_pic, first_logged_in, last_accessed):
    usuario = None
    try:
        usuario = await UserModel(username=user_name).get()
        # print(f'Usuario get: {usuario.toJSON()}')
        if usuario != None:
            await UserModel(id=usuario.id, username=user_name, email=user_email, password=usuario.password,
                            role=usuario.role,
                            avatar=user_pic, google_id=user_id).update()
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
        user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db_session)
):
    print(user.dict())
    creds = await GoogleCredential.getFromUser(user_id=user.google_id)
    print(creds.to_dict())
    if not creds or creds.expires_at < datetime.utcnow():
        raise HTTPException(403, "Reautenticación requerida con Google")
    return creds


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
async def login(request: Request, db: AsyncSession = Depends(get_db_session)):
    request.session.clear()
    referer = request.headers.get("referer")
    frontend_url = os.getenv("FRONTEND_URL")
    redirect_url = os.getenv("REDIRECT_URL")
    request.session["login_redirect"] = frontend_url
    return await oauth.auth_demo.authorize_redirect(request, redirect_url, prompt="consent")


@router.get("/auth/google")
async def auth(request: Request, db: AsyncSession = Depends(get_db_session)):
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
    first_logged_in = datetime.utcnow()
    last_accessed = datetime.utcnow()

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
    print(f'Access Token: {access_token}')
    print(f'Access Token Google: ' + token['access_token'])
    print(f'Time when expire: {datetime.now() + timedelta(seconds=token["expires_in"])}')
    print(f'Time Now: {datetime.now()}')
    print(f'Time expire ine: {timedelta(seconds=token["expires_in"])}')
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
            expires_at=datetime.now() + timedelta(seconds=token['expires_in'])
        ).update()
    else:
        await GoogleCredential(
            user_id=user_id,
            access_token=token['access_token'],
            refresh_token=token.get('refresh_token'),
            expires_at=datetime.now() + timedelta(seconds=token['expires_in'])
        ).create()
    return response


@router.get("/testDB")
async def test(
        creds: GoogleCredential = Depends(get_google_creds)):
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    creds2 = Credentials(token=creds.access_token)
    print(creds.to_dict())
    service = build('calendar', 'v3', credentials=creds2)
    print(service.calendarList().list().execute())
    return service.calendarList().list().execute()


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    response = JSONResponse(content={"message": "Logged out successfully."})
    response.delete_cookie("access_token")
    return response


@router.post("/login", tags=["Login"])
async def login_for_access_token(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: AsyncSession = Depends(get_db_session)
) -> Token:
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=User)
async def read_users_me(
        current_user: Annotated[User, Depends(get_current_active_user)], db: AsyncSession = Depends(get_db_session)
):
    return current_user

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
