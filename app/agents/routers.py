import json

from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.security import HTTPBearer
from sqlalchemy.future import select
from fastapi.responses import JSONResponse

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
# from app.agents.models import Agent
# from app.agents.schemas import AgentCreate,AgentResponse
from .schemas import AgentCreate, AgentResponse
from .models import Agent
from app.db.session import get_db_session

router = APIRouter()


@router.post("/agents/", response_model=AgentResponse)
async def create_agent(agent: AgentCreate, db: AsyncSession = Depends(get_db_session)):
    try:
        new_agent = Agent(**agent.dict())
        await new_agent.create()
        # db.add(new_agent)
        # await db.commit()
        # await db.refresh(new_agent)
        return new_agent.to_dict()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: int, agent: AgentCreate, db: AsyncSession = Depends(get_db_session)):
    try:
        print(f"id:{agent_id}, Type: {agent_id.__class__}")
        print(f"Agente :{agent}, Type: {agent.__class__}")
        new_agent = Agent(id=agent_id, **agent.dict())
        print(f"Agente 2: {new_agent}, Type: {new_agent.__class__}")
        await new_agent.update()

        # return new_agent.to_dict()
        return JSONResponse(content={"message": "El agente a sido actualizado"}, status_code=200)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: int, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    return JSONResponse(content=agent.to_dict(), status_code=200)


@router.delete("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: int, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar()

    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    return JSONResponse(content=agent.to_dict(), status_code=200)


@router.get("/agents", response_model=None)
async def get_agent(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(Agent))
    agents = result.scalars().all()
    print({'agents': [agent.to_dict() for agent in agents]})
    if not agents:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    return JSONResponse(content={'agents': [agent.to_dict() for agent in agents]}, status_code=200)


@router.get("/agents/{agent_id}/makeCalls", response_model=None)
async def agent_make_calls(agent_id: int, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar()
    await agent.make_call(db)

    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    # return JSONResponse(content=agent.to_dict(), status_code=200)
