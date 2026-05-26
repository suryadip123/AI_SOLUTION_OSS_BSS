from langchain_core.tools import tool

MONITORED_ACCOUNTS = [
    "ENT-001", "ENT-002", "ENT-003",
    "SMB-001", "SMB-002", "SMB-003",
    "RTL-001", "RTL-002",
    "GOV-001", "GOV-002",
]

# direction "below" = lower value is worse; "above" = higher value is worse
THRESHOLDS = {
    "order_completion_rate": {"warning": 85.0, "critical": 70.0, "direction": "below"},
    "avg_fulfillment_time":  {"warning": 48.0, "critical": 72.0, "direction": "above"},
    "sla_breach_rate":       {"warning":  5.0, "critical": 15.0, "direction": "above"},
}

@tool
def list_monitored_accounts() -> str:
    """Return the list of customer accounts under active health monitoring."""
    return ", ".join(MONITORED_ACCOUNTS)

@tool
def get_customer_thresholds() -> str:
    """Return the SLA and order-health threshold configuration."""
    lines = []
    for metric, cfg in THRESHOLDS.items():
        lines.append(
            f"{metric}: warning={'<' if cfg['direction']=='below' else '>'}{cfg['warning']}, "
            f"critical={'<' if cfg['direction']=='below' else '>'}{cfg['critical']}"
        )
    return "\n".join(lines)

TOOLS = [list_monitored_accounts, get_customer_thresholds]
