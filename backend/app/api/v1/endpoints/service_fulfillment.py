from fastapi import APIRouter, Depends
from app.schemas.agent import AgentRequest, AgentResponse
from app.agents.service_fulfillment.graph import run_agent

router = APIRouter()

@router.post("/run", response_model=AgentResponse)
async def run_service_fulfillment_agent(request: AgentRequest):
    """Invoke the Service Fulfillment Agent via LangGraph."""
    result = await run_agent(request.dict())
    return AgentResponse(agent="service_fulfillment", result=result)

@router.get("/status")
async def get_status():
    return {"agent": "service_fulfillment", "status": "ready"}
