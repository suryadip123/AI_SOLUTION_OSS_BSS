from langchain_core.tools import tool

THRESHOLDS = {
    "bill_gen_success_rate":    {"warning": 95.0, "critical": 85.0, "direction": "below"},
    "payment_collection_rate":  {"warning": 90.0, "critical": 75.0, "direction": "below"},
    "dispute_rate":             {"warning":  3.0, "critical":  8.0, "direction": "above"},
}

@tool
def get_billing_thresholds() -> str:
    """Return billing health monitoring thresholds."""
    return str(THRESHOLDS)

TOOLS = [get_billing_thresholds]
