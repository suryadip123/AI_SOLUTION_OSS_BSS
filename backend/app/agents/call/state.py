from typing import TypedDict, Annotated, Any
from langgraph.graph.message import add_messages

class CallState(TypedDict):
    messages: Annotated[list, add_messages]
    session_id: str
    query: str
    context: dict[str, Any]
    result: Any
    status: str
