from app.agents.base_agent import get_llm
from langchain_core.messages import HumanMessage, SystemMessage

llm = get_llm()

SYSTEM_PROMPT = """You are the Master Orchestrator for a Telecom OSS/BSS AI system.
You coordinate 7 specialized agents: Network, Customer, Service Fulfillment,
Service Assurance, Billing, Call, and Social Media.
Analyze the incoming query and decide which agents to invoke and in what order.
Always return a structured JSON with keys: agents_to_invoke, reasoning, priority."""

async def orchestrate_node(state):
    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=state["query"])]
    response = await llm.ainvoke(messages)
    return {"messages": [response], "final_summary": response.content}
