from typing import TypedDict, Annotated, Any
from langgraph.graph.message import add_messages

class BillingState(TypedDict):
    messages:        Annotated[list, add_messages]
    session_id:      str
    query:           str
    context:         dict[str, Any]
    billing_reports: list[dict]
    alerts:          list[dict]
    result:          Any
    status:          str
