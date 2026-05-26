from langchain_core.tools import tool

THRESHOLDS = {
    "call_success_rate": {"warning": 95.0, "critical": 90.0, "direction": "below"},
    "call_drop_rate":    {"warning":  3.0, "critical":  7.0, "direction": "above"},
    "avg_duration_min":  {"warning":  2.0, "critical":  1.0, "direction": "below"},
}

@tool
def get_call_thresholds() -> str:
    """Return call analytics monitoring thresholds."""
    return str(THRESHOLDS)

TOOLS = [get_call_thresholds]
