from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.agents.agent import run_agent
from app.agents.state import AgentState
from app.core.security import Role, require_role

router = APIRouter(prefix="/agent", tags=["agent"])


class AgentQueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


@router.post("/query", response_model=AgentState, dependencies=[Depends(require_role(Role.ADMIN, Role.ANALYST, Role.VIEWER))])
def agent_query(request: AgentQueryRequest) -> AgentState:
    return run_agent(request.question)
