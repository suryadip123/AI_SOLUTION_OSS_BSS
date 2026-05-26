from langchain_core.tools import tool

SLA_HOURS = {
    "SIM_ACTIVATION":  2,
    "BROADBAND":       24,
    "NUMBER_PORTING":  72,
}

STEP_BASELINE_SECONDS = {
    "Validate":          30.0,
    "Allocate Resource": 120.0,
    "Configure":         180.0,
    "Activate":          240.0,
    "Confirm":           60.0,
}

ALERT_TYPES = {
    "SLA_BREACH":            "CRITICAL",
    "SLA_AT_RISK":           "HIGH",
    "STEP_FAILURE":          "HIGH",
    "FULFILLMENT_DELAY":     "MEDIUM",
}

ORDER_STATUSES = ["PENDING", "VALIDATING", "PROVISIONING", "TESTING", "COMPLETED", "FAILED"]

@tool
def get_sla_config() -> str:
    """Return SLA thresholds and alert severity mappings for service fulfillment orders."""
    lines = [f"{k}: {v}h SLA" for k, v in SLA_HOURS.items()]
    lines += [f"{k}: {v} severity" for k, v in ALERT_TYPES.items()]
    return "\n".join(lines)

@tool
def get_step_baselines() -> str:
    """Return average baseline durations per provisioning step."""
    return "\n".join([f"{k}: {v}s avg" for k, v in STEP_BASELINE_SECONDS.items()])

TOOLS = [get_sla_config, get_step_baselines]
