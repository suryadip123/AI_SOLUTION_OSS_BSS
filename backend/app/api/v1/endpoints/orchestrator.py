from fastapi import APIRouter, Depends
from app.schemas.agent import AgentRequest, AgentResponse
from app.agents.orchestrator.graph import run_agent

router = APIRouter()

@router.post("/run", response_model=AgentResponse)
async def run_orchestrator_agent(request: AgentRequest):
    """Invoke the Orchestrator Agent via LangGraph."""
    result = await run_agent(request.dict())
    return AgentResponse(agent="orchestrator", result=result)

@router.get("/status")
async def get_status():
    return {"agent": "orchestrator", "status": "ready"}
