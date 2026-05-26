from fastapi import APIRouter, Depends
from app.schemas.agent import AgentRequest, AgentResponse
from app.agents.network.graph import run_agent

router = APIRouter()

@router.post("/run", response_model=AgentResponse)
async def run_network_agent(request: AgentRequest):
    """Invoke the Network Agent via LangGraph."""
    result = await run_agent(request.dict())
    return AgentResponse(agent="network", result=result)

@router.get("/status")
async def get_status():
    return {"agent": "network", "status": "ready"}
