from fastapi import APIRouter, Depends
from app.schemas.agent import AgentRequest, AgentResponse
from app.agents.service_assurance.graph import run_agent

router = APIRouter()

@router.post("/run", response_model=AgentResponse)
async def run_service_assurance_agent(request: AgentRequest):
    """Invoke the Service Assurance Agent via LangGraph."""
    result = await run_agent(request.dict())
    return AgentResponse(agent="service_assurance", result=result)

@router.get("/status")
async def get_status():
    return {"agent": "service_assurance", "status": "ready"}
