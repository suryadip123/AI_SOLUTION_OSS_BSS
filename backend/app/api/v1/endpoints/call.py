from fastapi import APIRouter, Depends
from app.schemas.agent import AgentRequest, AgentResponse
from app.agents.call.graph import run_agent

router = APIRouter()

@router.post("/run", response_model=AgentResponse)
async def run_call_agent(request: AgentRequest):
    """Invoke the Call Agent via LangGraph."""
    result = await run_agent(request.dict())
    return AgentResponse(agent="call", result=result)

@router.get("/status")
async def get_status():
    return {"agent": "call", "status": "ready"}
