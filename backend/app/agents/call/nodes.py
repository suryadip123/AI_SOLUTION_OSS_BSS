from app.agents.base_agent import get_llm
from app.agents.call.tools import TOOLS
from langchain_core.messages import HumanMessage

llm = get_llm()
llm_with_tools = llm.bind_tools(TOOLS)

async def query_node(state):
    """Entry node: build prompt and call LLM."""
    messages = state["messages"] + [HumanMessage(content=state["query"])]
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response], "result": response.content}

async def tool_node(state):
    """Execute any tool calls returned by the LLM."""
    from langgraph.prebuilt import ToolNode
    tool_executor = ToolNode(TOOLS)
    return await tool_executor.ainvoke(state)

def should_continue(state) -> str:
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else "end"
