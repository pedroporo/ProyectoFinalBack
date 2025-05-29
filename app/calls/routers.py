import csv
import re
import requests

from twilio.rest import Client

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse,StreamingResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.models import Database
from app.users.models import User
from app.users.routers import get_current_active_user
from app.users.routers import get_user_db_session_class, get_user_db
from .models import Call,Transcription
from .schemas import CallCreate, CallResponse

router = APIRouter(prefix="/calls", tags=["Calls"])


@router.post("/", response_model=CallResponse, summary="Create call")
async def create_call(call: CallCreate, db: Database = Depends(get_user_db),
                      current_user: User = Depends(get_current_active_user)):
    """
                Crea una llamada en la base de datos del usuario:

                - **contact_name**: El nombre del contacto de la llamada.
                - **agent_id**: La id del agente al que se le asignara la llamada.
                - **status**: El estado de la llamada.
                - **phone_number**: El numero de telefono del contacto.
                \f
                :agent_id: Id del agente.
                """
    try:
        new_call = Call(**call.dict())
        await new_call.create()
        return new_call.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/upload_csv/{agent_id}", summary="Cargar llamadas desde un archivo CSV")
async def upload_calls_csv(
        agent_id: int,
        file: UploadFile = File(...),
        db: Database = Depends(get_user_db),
        current_user: User = Depends(get_current_active_user)
):
    """
                    Sube un csv para crear un monton de llamadas en la base de datos del usuario:

                    - **file**: El archivo de las llamadas.
                    - **agent_id**: La id del agente al que se le asignara la llamada.
                    \f
                    :agent_id: Id del agente.
                    """
    max_length = Call.__table__.columns["contact_name"].type.length
    if file.content_type != "text/csv":
        raise HTTPException(status_code=400, detail="El archivo debe ser un CSV")

    content = await file.read()
    content_str = content.decode("utf-8-sig")
    lines = content_str.splitlines()

    if lines and lines[0].startswith("sep="):
        lines = lines[1:]
    column_names = [s.strip('"') for s in lines[0].split(",")]
    reader = csv.DictReader(lines, fieldnames=column_names, quotechar='"')
    if "Name" not in reader.fieldnames or "Phone" not in reader.fieldnames:
        raise HTTPException(status_code=400, detail="El CSV debe tener columnas 'Name' y 'Phone'")

    created_calls = []
    for row in reader:
        name = row.get("Name")
        phone = row.get("Phone")
        if not name or not phone or name == "Name" or phone == "Phone":
            continue

        if name and phone:
            # Limpiar el nombre
            delimiters = r" - | \| |, |-"
            name = re.split(delimiters, name)[0].strip()
            if len(name) > max_length:
                name = name[:max_length]
            phone_clean = phone.replace(" ", "")
            if not phone_clean.startswith("+34"):
                phone_clean = "+34" + phone_clean.lstrip("+")
            call = Call(contact_name=name, phone_number=phone_clean, agent_id=agent_id)
            await call.create()
            created_calls.append(call.to_dict())

    return {"message": f"{len(created_calls)} llamadas agregadas", "calls": created_calls}


@router.get("/{call_id}", response_model=CallResponse, summary="Get call")
async def get_call(call_id: int, db: Database = Depends(get_user_db),
                   current_user: User = Depends(get_current_active_user)):
    """
                    Busca una llamada en la base de datos del usuario:

                    - **call_id**: La id de la llamada que estamos buscando.
                    \f
                    :agent_id: Id del agente.
                    """
    call = await Call(id=call_id).get()
    if not call:
        raise HTTPException(status_code=404, detail="Llamada no encontrado")
    return call.to_dict()


@router.put("/{call_id}", response_model=CallResponse, summary="Update call")
async def update_call(call_id: int, call: CallCreate, db: Database = Depends(get_user_db),
                      current_user: User = Depends(get_current_active_user)):
    """
                    Actualiza una llamada en la base de datos del usuario:

                    - **contact_name**: El nombre del contacto de la llamada.
                    - **agent_id**: La id del agente al que se le asignara la llamada.
                    - **status**: El estado de la llamada.
                    - **phone_number**: El numero de telefono del contacto.
                    \f
                    :agent_id: Id del agente.
                    """
    try:
        new_call = Call(id=call_id, **call.dict())
        await new_call.update()
        return JSONResponse(content={"message": "La llamada a sido actualizada"}, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{call_id}", response_model=CallResponse, summary="Delete call")
async def del_call(call_id: int, db: Database = Depends(get_user_db),
                   current_user: User = Depends(get_current_active_user)):
    """
                    Elimina una llamada en la base de datos del usuario:

                    - **contact_name**: El nombre del contacto de la llamada.
                    - **agent_id**: La id del agente al que se le asignara la llamada.
                    - **status**: El estado de la llamada.
                    - **phone_number**: El numero de telefono del contacto.
                    \f
                    :agent_id: Id del agente.
                    """
    call = await Call(id=call_id).get()
    await call.delete()
    if not call:
        raise HTTPException(status_code=404, detail="Llamada no encontrado")
    return JSONResponse(content={"message": "La llamada a sido eliminada"}, status_code=200)


@router.get("/a/{agent_id}", response_model=None, tags=["Agents"], summary="Get calls from agent")
async def get_agents_call(agent_id: int, db: AsyncSession = Depends(get_user_db_session_class),
                          current_user: User = Depends(get_current_active_user)):
    """
                    Busca una llamada de un agente en la base de datos del usuario:

                    - **contact_name**: El nombre del contacto de la llamada.
                    - **agent_id**: La id del agente al que se le asignara la llamada.
                    - **status**: El estado de la llamada.
                    - **phone_number**: El numero de telefono del contacto.
                    \f
                    :agent_id: Id del agente.
                    """
    result = await db.execute(select(Call).where(Call.agent_id == agent_id))
    llamadas = result.scalars().all()
    if not llamadas and llamadas != []:
        raise HTTPException(status_code=404, detail="Llamadas no encontrado")
    return JSONResponse(content=jsonable_encoder({'calls': [llamada.to_dict() for llamada in llamadas]}), status_code=200)
@router.get("/{call_id}/transcription", summary="Get call transcription")
async def get_transcription(call_id: str, db: Database = Depends(get_user_db),
                   current_user: User = Depends(get_current_active_user)):
    """
                    Busca la transcripccion de una llamada en la base de datos del usuario:

                    - **contact_name**: El nombre del contacto de la llamada.
                    - **agent_id**: La id del agente al que se le asignara la llamada.
                    - **status**: El estado de la llamada.
                    - **phone_number**: El numero de telefono del contacto.
                    \f
                    :agent_id: Id del agente.
                    """
    transcription=await Transcription(call_id=call_id).getBySid()
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcripccion no encontrada")
    return JSONResponse(content=jsonable_encoder(transcription.to_dict()), status_code=200)
@router.get("/{call_id}/recording", summary="Get call transcription")
async def get_recording(call_id: str, db: Database = Depends(get_user_db),
                   current_user: User = Depends(get_current_active_user)):
    """
                    Busca la grabacion de una llamada:

                    - **contact_name**: El nombre del contacto de la llamada.
                    - **agent_id**: La id del agente al que se le asignara la llamada.
                    - **status**: El estado de la llamada.
                    - **phone_number**: El numero de telefono del contacto.
                    \f
                    :agent_id: Id del agente.
                    """
    try:
        twilio_account_sid = current_user.config_user['credentials']['TWILIO_ACCOUNT_SID']
        twilio_auth_token = current_user.config_user['credentials']['TWILIO_AUTH_TOKEN']

        client = Client(twilio_account_sid, twilio_auth_token)

        recordings = client.recordings.list(call_sid=call_id)

        if not recordings:
            raise HTTPException(status_code=404, detail="No se encontraron grabaciones")

        recording_uri = recordings[0].uri.replace(".json", ".mp3")
        mp3_url = f"https://api.twilio.com{recording_uri}"
        #print(f"Get file: {mp3_url}")
        response = requests.get(
            mp3_url,
            auth=(twilio_account_sid, twilio_auth_token),
            stream=True
        )

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Error al obtener la grabación")

        return StreamingResponse(
            response.iter_content(chunk_size=8192),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"attachment; filename=recording_{call_id}.mp3",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))