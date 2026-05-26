from pydantic import BaseModel
from typing import Any, Optional

class AgentRequest(BaseModel):
    session_id: Optional[str] = None
    query: str
    context: Optional[dict[str, Any]] = {}

class AgentResponse(BaseModel):
    agent: str
    result: Any
    status: str = "success"
