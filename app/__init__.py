from fastapi import APIRouter
from .agents import agent_router
from .calls import call_router
from .users import user_router

router = APIRouter(prefix="/api")
router.include_router(agent_router)
router.include_router(call_router)
router.include_router(user_router)
