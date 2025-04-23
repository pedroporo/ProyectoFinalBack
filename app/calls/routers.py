from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.security import HTTPBearer
from sqlalchemy.future import select
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from .schemas import CallCreate, CallResponse
from .models import Call
from app.db.session import get_db_session
from app.users.routers import get_current_active_user
from typing import Annotated
from app.users.models import User, GoogleCredential

router = APIRouter(prefix="/calls", tags=["Calls"])


@router.post("/", response_model=CallResponse, summary="Create call")
async def create_call(call: CallCreate, db: AsyncSession = Depends(get_db_session),
                      current_user: User = Depends(get_current_active_user)):
    try:
        new_call = Call(**call.dict())
        await new_call.create(db=await current_user.get_user_database())
        # db.add(new_agent)
        # await db.commit()
        # await db.refresh(new_agent)
        return new_call.to_dict()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{call_id}", response_model=CallResponse, summary="Get call")
async def get_call(call_id: int, db: AsyncSession = Depends(get_db_session),
                   current_user: User = Depends(get_current_active_user)):
    print(current_user.config_user)
    # result = await db.execute(select(Call).where(Call.id == call_id))
    # call = result.scalar()
    call = await Call(id=call_id).get(db=await current_user.get_user_database())
    print(f'Call:{call.to_dict()}')
    if not call:
        raise HTTPException(status_code=404, detail="Llamada no encontrado")
    return call.to_dict()


@router.put("/{call_id}", response_model=CallResponse, summary="Update call")
async def update_call(call_id: int, call: CallCreate, db: AsyncSession = Depends(get_db_session),
                      current_user: User = Depends(get_current_active_user)):
    try:
        new_call = Call(id=call_id, **call.dict())
        await new_call.update(db=await current_user.get_user_database())
        return JSONResponse(content={"message": "La llamada a sido actualizada"}, status_code=200)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{call_id}", response_model=CallResponse, summary="Delete call")
async def del_call(call_id: int, db: AsyncSession = Depends(get_db_session),
                   current_user: User = Depends(get_current_active_user)):
    # result = await db.execute(select(Call).where(Call.id == call_id))
    # call = result.scalar()
    call = await Call(id=call_id).get(db=await current_user.get_user_database())
    await call.delete()
    if not call:
        raise HTTPException(status_code=404, detail="Llamada no encontrado")
    return JSONResponse(content={"message": "La llamada a sido eliminada"}, status_code=200)


@router.get("/{agent_id}", response_model=None, tags=["Agents"], summary="Get calls from agent")
async def get_agents_call(agent_id: int, db: AsyncSession = Depends(get_db_session),
                          current_user: User = Depends(get_current_active_user)):
    result = await db.execute(select(Call).where(Call.agent_id == agent_id))
    llamadas = result.scalars().all()
    # print({'agents': [agent.to_dict() for agent in agents]})
    if not llamadas:
        raise HTTPException(status_code=404, detail="Llamadas no encontrado")
    return JSONResponse(content={'calls': [llamada.to_dict() for llamada in llamadas]}, status_code=200)
