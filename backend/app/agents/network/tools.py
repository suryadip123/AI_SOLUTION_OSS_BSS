from langchain_core.tools import tool

MONITORED_DEVICES = [
    "Router-01", "Router-02", "Router-03",
    "Switch-01", "Switch-02",
    "OLT-01",    "OLT-02",
    "BTS-North", "BTS-South", "BTS-East",
]

THRESHOLDS = {
    "cpu":         {"warning": 70.0, "critical": 90.0},
    "packet_loss": {"warning":  2.0, "critical":  5.0},
    "latency":     {"warning": 100.0, "critical": 300.0},
}

@tool
def list_monitored_devices() -> str:
    """Return the list of network devices under active monitoring."""
    return ", ".join(MONITORED_DEVICES)

@tool
def get_threshold_config() -> str:
    """Return the current alert threshold configuration for all metrics."""
    lines = []
    for metric, vals in THRESHOLDS.items():
        lines.append(f"{metric}: warning>{vals['warning']}, critical>{vals['critical']}")
    return "\n".join(lines)

@tool
def check_device_status(device_name: str) -> str:
    """Look up the last known health status for a specific device by name."""
    # This tool is called by the LLM during analysis; the node layer handles DB reads.
    return f"Query the fetch_metrics_node result for device: {device_name}"

TOOLS = [list_monitored_devices, get_threshold_config, check_device_status]
