from langgraph.graph import StateGraph, END
from app.agents.orchestrator.state import OrchestratorState
from app.agents.orchestrator.nodes import orchestrate_node

def build_graph():
    g = StateGraph(OrchestratorState)
    g.add_node("orchestrate", orchestrate_node)
    g.set_entry_point("orchestrate")
    g.add_edge("orchestrate", END)
    return g.compile()

_graph = build_graph()

async def run_agent(payload: dict):
    state = {
        "messages":     [],
        "query":        payload.get("query", ""),
        "active_agents": [],
        "agent_results": {},
        "final_summary": "",
    }
    result = await _graph.ainvoke(state)
    return result.get("final_summary", "")
