from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.models import Agent,VoiceOptionsEnum
from .schemas import AgentCreate,AgentResponse
from app.db.session import get_db_session
app=APIRouter()

@app.post("/agents/",response_class=JSONResponse,response_model=AgentResponse)
async def create_agent(agent:AgentCreate,db:AsyncSession=Depends(get_db_session)):
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return JSONResponse(status_code=status.HTTP_200_OK,content=jsonable_encoder(agent.toJSON()))

@app.get("/agents/{agent_id}")
async def get_agent(agent_id: int, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(db.select(Agent).where(Agent.id == agent_id))
    agent = result.scalar()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    return JSONResponse(content=agent.toJSON(), status_code=200)
