from fastapi import APIRouter, Depends
from app.schemas.agent import AgentRequest, AgentResponse
from app.agents.customer.graph import run_agent

router = APIRouter()

@router.post("/run", response_model=AgentResponse)
async def run_customer_agent(request: AgentRequest):
    """Invoke the Customer Agent via LangGraph."""
    result = await run_agent(request.dict())
    return AgentResponse(agent="customer", result=result)

@router.get("/status")
async def get_status():
    return {"agent": "customer", "status": "ready"}
