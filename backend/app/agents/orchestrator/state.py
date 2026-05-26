from typing import TypedDict, Annotated, Any
from langgraph.graph.message import add_messages

class OrchestratorState(TypedDict):
    messages: Annotated[list, add_messages]
    query: str
    active_agents: list[str]
    agent_results: dict[str, Any]
    final_summary: str
