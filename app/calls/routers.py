from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.security import HTTPBearer
from sqlalchemy.future import select
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from .schemas import CallCreate,CallResponse
from .models import Call
from app.db.session import get_db_session
router=APIRouter()

@router.post("/calls/",response_model=CallResponse)
async def create_call(call:CallCreate,db:AsyncSession=Depends(get_db_session)):
    try:
        new_agent = Call(**call.dict())

        db.add(new_agent)
        await db.commit()
        await db.refresh(new_agent)
        return new_agent.to_dict()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/calls/{call_id}",response_model=CallResponse)
async def get_agent(call_id: int, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(Call).where(Call.id == call_id))
    agent = result.scalar()
    if not agent:
        raise HTTPException(status_code=404, detail="Llamada no encontrado")
    return JSONResponse(content=agent.to_dict(), status_code=200)
