from fastapi import APIRouter, Depends
from app.schemas.agent import AgentRequest, AgentResponse
from app.agents.social_media.graph import run_agent

router = APIRouter()

@router.post("/run", response_model=AgentResponse)
async def run_social_media_agent(request: AgentRequest):
    """Invoke the Social Media Agent via LangGraph."""
    result = await run_agent(request.dict())
    return AgentResponse(agent="social_media", result=result)

@router.get("/status")
async def get_status():
    return {"agent": "social_media", "status": "ready"}
