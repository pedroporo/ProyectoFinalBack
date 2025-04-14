import json

from fastapi import APIRouter, Depends, status, HTTPException, Request, Cookie
from fastapi.encoders import jsonable_encoder
from fastapi.security import HTTPBearer
from sqlalchemy.future import select
from fastapi.responses import JSONResponse

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
# from app.agents.models import Agent
# from app.agents.schemas import AgentCreate,AgentResponse
from .schemas import AgentCreate, AgentResponse
from .models import Agent
from app.db.session import get_db_session
from app.users.models import GoogleCredential
from app.users.routers import get_google_creds

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.post("/", response_model=AgentResponse)
async def create_agent(agent: AgentCreate, db: AsyncSession = Depends(get_db_session)):
    try:
        new_agent = Agent(**agent.dict())
        await new_agent.create()
        # db.add(new_agent)
        # await db.commit()
        # await db.refresh(new_agent)
        return new_agent.to_dict()
    except Exception as e:
        # await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: int, agent: AgentCreate, db: AsyncSession = Depends(get_db_session)):
    try:
        # print(f"id:{agent_id}, Type: {agent_id.__class__}")
        # print(f"Agente :{agent}, Type: {agent.__class__}")
        new_agent = Agent(id=agent_id, **agent.dict())
        # print(f"Agente 2: {new_agent}, Type: {new_agent.__class__}")
        await new_agent.update()

        # return new_agent.to_dict()
        return JSONResponse(content={"message": "El agente a sido actualizado"}, status_code=200)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: int, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    return JSONResponse(content=agent.to_dict(), status_code=200)


@router.delete("/{agent_id}", response_model=None, description="Eliminar un agente", summary="Delete agent")
async def get_agent(agent_id: int, db: AsyncSession = Depends(get_db_session)):
    # result = await db.execute(select(Agent).where(Agent.id == agent_id))
    # agent = result.scalar()
    agent = await Agent(id=agent_id).get()
    await agent.delete()
    # print(f'Agente despues del delete: {agent.to_dict()}')
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    return JSONResponse(content={"message": "El agente a sido eliminado"}, status_code=200)


@router.get("/", response_model=None)
async def get_agent(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(Agent))
    agents = result.scalars().all()
    # print({'agents': [agent.to_dict() for agent in agents]})
    if not agents:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    return JSONResponse(content={'agents': [agent.to_dict() for agent in agents]}, status_code=200)


@router.get("/{agent_id}/makeCalls", response_model=None)
async def agent_make_calls(request: Request, agent_id: int, db: AsyncSession = Depends(get_db_session),
                           creds: GoogleCredential = Depends(get_google_creds)):
    agent = await Agent(id=agent_id).get()
    agent.googleCreds = creds.access_token
    await agent.make_call(db)

    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    # return JSONResponse(content=agent.to_dict(), status_code=200)
