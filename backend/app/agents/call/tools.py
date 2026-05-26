from langchain_core.tools import tool

@tool
def fetch_call_data(query: str) -> str:
    """Fetch Call domain data from the local SQLite database."""
    # TODO: Implement real DB query via SQLAlchemy
    return f"[Mock] Call data for query: {query}"

@tool
def analyze_call_metrics(data: str) -> str:
    """Analyze Call metrics and return insights."""
    # TODO: Implement ML-based analysis
    return f"[Mock] Insights for: {data}"

TOOLS = [fetch_call_data, analyze_call_metrics]
