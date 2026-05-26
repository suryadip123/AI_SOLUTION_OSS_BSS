from fastapi import APIRouter, Depends
from app.schemas.agent import AgentRequest, AgentResponse
from app.agents.billing.graph import run_agent

router = APIRouter()

@router.post("/run", response_model=AgentResponse)
async def run_billing_agent(request: AgentRequest):
    """Invoke the Billing Agent via LangGraph."""
    result = await run_agent(request.dict())
    return AgentResponse(agent="billing", result=result)

@router.get("/status")
async def get_status():
    return {"agent": "billing", "status": "ready"}
