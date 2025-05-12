import csv
import re

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.models import Database
from app.users.models import User
from app.users.routers import get_current_active_user
from app.users.routers import get_user_db_session, get_user_db
from .models import Call
from .schemas import CallCreate, CallResponse

router = APIRouter(prefix="/calls", tags=["Calls"])


@router.post("/", response_model=CallResponse, summary="Create call")
async def create_call(call: CallCreate, db: Database = Depends(get_user_db),
                      current_user: User = Depends(get_current_active_user)):
    try:
        new_call = Call(**call.dict())
        await new_call.create()
        # db.add(new_agent)
        # await db.commit()
        # await db.refresh(new_agent)
        return new_call.to_dict()
    except Exception as e:
        # await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/upload_csv/{agent_id}", summary="Cargar llamadas desde un archivo CSV")
async def upload_calls_csv(
        agent_id: int,
        file: UploadFile = File(...),
        db: Database = Depends(get_user_db),
        current_user: User = Depends(get_current_active_user)
):
    max_length = Call.__table__.columns["contact_name"].type.length
    # print(file.content_type)
    if file.content_type != "text/csv":
        raise HTTPException(status_code=400, detail="El archivo debe ser un CSV")

    content = await file.read()
    content_str = content.decode("utf-8-sig")
    lines = content_str.splitlines()

    if lines and lines[0].startswith("sep="):
        lines = lines[1:]
    column_names = [s.strip('"') for s in lines[0].split(",")]
    reader = csv.DictReader(lines, fieldnames=column_names, quotechar='"')
    # print(reader.fieldnames)
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
            # print(f'Call: {call.to_dict()}')
            created_calls.append(call.to_dict())

    return {"message": f"{len(created_calls)} llamadas agregadas", "calls": created_calls}


@router.get("/{call_id}", response_model=CallResponse, summary="Get call")
async def get_call(call_id: int, db: Database = Depends(get_user_db),
                   current_user: User = Depends(get_current_active_user)):
    # print(current_user.config_user)
    # result = await db.execute(select(Call).where(Call.id == call_id))
    # call = result.scalar()
    call = await Call(id=call_id).get()
    # print(f'Call:{call.to_dict()}')
    if not call:
        raise HTTPException(status_code=404, detail="Llamada no encontrado")
    return call.to_dict()


@router.put("/{call_id}", response_model=CallResponse, summary="Update call")
async def update_call(call_id: int, call: CallCreate, db: Database = Depends(get_user_db),
                      current_user: User = Depends(get_current_active_user)):
    try:
        new_call = Call(id=call_id, **call.dict())
        await new_call.update()
        return JSONResponse(content={"message": "La llamada a sido actualizada"}, status_code=200)
    except Exception as e:
        # await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{call_id}", response_model=CallResponse, summary="Delete call")
async def del_call(call_id: int, db: Database = Depends(get_user_db),
                   current_user: User = Depends(get_current_active_user)):
    # result = await db.execute(select(Call).where(Call.id == call_id))
    # call = result.scalar()
    call = await Call(id=call_id).get()
    await call.delete()
    if not call:
        raise HTTPException(status_code=404, detail="Llamada no encontrado")
    return JSONResponse(content={"message": "La llamada a sido eliminada"}, status_code=200)


@router.get("/{agent_id}", response_model=None, tags=["Agents"], summary="Get calls from agent")
async def get_agents_call(agent_id: int, db: AsyncSession = Depends(get_user_db_session),
                          current_user: User = Depends(get_current_active_user)):
    result = await db.execute(select(Call).where(Call.agent_id == agent_id))
    llamadas = result.scalars().all()
    # print({'agents': [agent.to_dict() for agent in agents]})
    if not llamadas and llamadas != []:
        raise HTTPException(status_code=404, detail="Llamadas no encontrado")
    return JSONResponse(content={'calls': [llamada.to_dict() for llamada in llamadas]}, status_code=200)
