from langchain_core.tools import tool

@tool
def fetch_billing_data(query: str) -> str:
    """Fetch Billing domain data from the local SQLite database."""
    # TODO: Implement real DB query via SQLAlchemy
    return f"[Mock] Billing data for query: {query}"

@tool
def analyze_billing_metrics(data: str) -> str:
    """Analyze Billing metrics and return insights."""
    # TODO: Implement ML-based analysis
    return f"[Mock] Insights for: {data}"

TOOLS = [fetch_billing_data, analyze_billing_metrics]
