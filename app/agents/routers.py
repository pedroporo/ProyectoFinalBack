from fastapi import APIRouter, Depends, HTTPException,Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.users.models import GoogleCredential
from app.users.models import User
from app.users.routers import get_current_active_user
from app.users.routers import get_google_creds, get_user_db_session, get_user_db,get_user_db_session_class
from .models import Agent
# from app.agents.models import Agent
# from app.agents.schemas import AgentCreate,AgentResponse
from .schemas import AgentCreate, AgentResponse
from ..db.models import Database

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.post("/", response_model=AgentResponse)
async def create_agent(agent: AgentCreate, db: Database = Depends(get_user_db)):
    try:
        new_agent = Agent(**agent.dict())
        await new_agent.create()
        return new_agent.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: int, agent: AgentCreate,
                       current_user: User = Depends(get_current_active_user),
                       db: Database = Depends(get_user_db)):
    try:
        new_agent = Agent(id=agent_id, **agent.dict())
        await new_agent.update()
        return JSONResponse(content={"message": "El agente a sido actualizado"}, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: int, db: Database = Depends(get_user_db),
                    current_user: User = Depends(get_current_active_user)):
    agent = await Agent(id=agent_id).get()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    return JSONResponse(content=agent.to_dict(), status_code=200)


@router.delete("/{agent_id}", response_model=None, description="Eliminar un agente", summary="Delete agent")
async def get_agent(agent_id: int, db: Database = Depends(get_user_db),
                    current_user: User = Depends(get_current_active_user)):
    agent = await Agent(id=agent_id).get()
    await agent.delete()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    return JSONResponse(content={"message": "El agente a sido eliminado"}, status_code=200)


@router.get("/", response_model=None)
async def get_agent(db: AsyncSession = Depends(get_user_db_session_class)):
    result = await db.execute(select(Agent))
    agents = result.scalars().all()
    if not agents and agents !=[]:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    return JSONResponse(content={'agents': [agent.to_dict() for agent in agents]}, status_code=200)


@router.get("/{agent_id}/makeCalls", response_model=None)
async def agent_make_calls(agent_id: int,request: Request, db: Database = Depends(get_user_db),
                           #creds: GoogleCredential = Depends(get_google_creds),
                           current_user: User = Depends(get_current_active_user)):
    token=request.cookies.get("access_token")
    print(token)
    agent = await Agent(id=agent_id).get()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    #agent.googleCreds = creds.access_token |None
    agent.googleCreds = None
    agent.user = current_user
    return JSONResponse(content=await agent.make_call(db,token), status_code=200)
