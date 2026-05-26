from langgraph.graph import StateGraph, END
from app.agents.call.state import CallState
from app.agents.call.nodes import fetch_metrics_node, analyze_alerts_node, should_analyze

def build_graph():
    g = StateGraph(CallState)
    g.add_node("fetch_metrics",  fetch_metrics_node)
    g.add_node("analyze_alerts", analyze_alerts_node)
    g.set_entry_point("fetch_metrics")
    g.add_conditional_edges("fetch_metrics", should_analyze, {"analyze": "analyze_alerts", "end": END})
    g.add_edge("analyze_alerts", END)
    return g.compile()

_graph = build_graph()

async def run_agent(payload: dict):
    state = {"messages": [], "session_id": payload.get("session_id",""), "query": payload.get("query",""),
             "context": payload.get("context",{}), "call_reports": [], "alerts": [], "result": None, "status": "running"}
    result = await _graph.ainvoke(state)
    return result.get("result")
