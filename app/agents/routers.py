from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.security import HTTPBearer
from sqlalchemy.future import select
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.models import Agent,VoiceOptionsEnum
from .schemas import AgentCreate,AgentResponse
from .models import Agent
from app.db.session import get_db_session
app=APIRouter()

@app.post("/agents/",response_model=AgentResponse)
async def create_agent(agent:AgentCreate,db:AsyncSession=Depends(get_db_session)):
    try:
        new_agent = Agent(**agent.dict())

        db.add(new_agent)
        await db.commit()
        await db.refresh(new_agent)
        return new_agent.to_dict()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/agents/{agent_id}",response_model=AgentResponse)
async def get_agent(agent_id: int, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    return JSONResponse(content=agent.to_dict(), status_code=200)
