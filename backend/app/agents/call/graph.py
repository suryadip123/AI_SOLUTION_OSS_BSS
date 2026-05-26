from langgraph.graph import StateGraph, END
from app.agents.call.state import CallState
from app.agents.call.nodes import query_node, tool_node, should_continue

def build_graph():
    g = StateGraph(CallState)
    g.add_node("llm",   query_node)
    g.add_node("tools", tool_node)
    g.set_entry_point("llm")
    g.add_conditional_edges("llm", should_continue, {"tools": "tools", "end": END})
    g.add_edge("tools", "llm")
    return g.compile()

_graph = build_graph()

async def run_agent(payload: dict):
    state = {
        "messages":   [],
        "session_id": payload.get("session_id", ""),
        "query":      payload.get("query", ""),
        "context":    payload.get("context", {}),
        "result":     None,
        "status":     "running",
    }
    result = await _graph.ainvoke(state)
    return result.get("result", "No result")
