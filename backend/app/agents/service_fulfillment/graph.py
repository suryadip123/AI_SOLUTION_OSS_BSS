from langgraph.graph import StateGraph, END
from app.agents.service_fulfillment.state import ServiceFulfillmentState
from app.agents.service_fulfillment.nodes import fetch_orders_node, analyze_rca_node, should_analyze


def build_graph():
    g = StateGraph(ServiceFulfillmentState)
    g.add_node("fetch_orders",  fetch_orders_node)
    g.add_node("analyze_rca",   analyze_rca_node)
    g.set_entry_point("fetch_orders")
    g.add_conditional_edges(
        "fetch_orders",
        should_analyze,
        {"analyze": "analyze_rca", "end": END},
    )
    g.add_edge("analyze_rca", END)
    return g.compile()


_graph = build_graph()


async def run_agent(payload: dict):
    state = {
        "messages":      [],
        "session_id":    payload.get("session_id", ""),
        "query":         payload.get("query", ""),
        "context":       payload.get("context", {}),
        "order_reports": [],
        "alerts":        [],
        "result":        None,
        "status":        "running",
    }
    result = await _graph.ainvoke(state)
    return result.get("result")
