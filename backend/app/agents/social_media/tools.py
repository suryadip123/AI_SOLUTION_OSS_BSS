from langchain_core.tools import tool

THRESHOLDS = {
    "nps_score":          {"warning": 30.0,  "critical":  0.0,  "direction": "below"},
    "negative_sentiment": {"warning": 20.0,  "critical": 40.0,  "direction": "above"},
    "complaint_volume":   {"warning": 50.0,  "critical": 100.0, "direction": "above"},
}

@tool
def get_social_media_thresholds() -> str:
    """Return social media sentiment monitoring thresholds."""
    return str(THRESHOLDS)

TOOLS = [get_social_media_thresholds]
