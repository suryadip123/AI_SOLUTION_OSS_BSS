from langchain_core.tools import tool

THRESHOLDS = {
    "availability_pct": {"warning": 99.5, "critical": 99.0, "direction": "below"},
    "error_rate_pct":   {"warning":  2.0, "critical":  5.0, "direction": "above"},
    "mttr_hours":       {"warning":  4.0, "critical":  8.0, "direction": "above"},
}

@tool
def get_service_assurance_thresholds() -> str:
    """Return service health monitoring thresholds."""
    return str(THRESHOLDS)

TOOLS = [get_service_assurance_thresholds]
