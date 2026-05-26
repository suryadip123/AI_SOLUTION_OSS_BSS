from typing import TypedDict, Annotated, Any
from langgraph.graph.message import add_messages

class NetworkState(TypedDict):
    messages:       Annotated[list, add_messages]
    session_id:     str
    query:          str
    context:        dict[str, Any]
    device_reports: list[dict]
    alerts:         list[dict]
    result:         Any
    status:         str
