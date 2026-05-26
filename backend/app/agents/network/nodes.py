import json
import re
import random
from datetime import datetime, timezone
from sqlalchemy import select
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base_agent import get_llm
from app.db.database import AsyncSessionLocal
from app.db.models.network import NetworkDevice
from app.agents.network.tools import MONITORED_DEVICES, THRESHOLDS

llm = get_llm()


def _jitter(base: float, pct: float = 0.20, lo: float = 0.0, hi: float = 100.0) -> float:
    """Apply ±pct random variation around base value, clamped to [lo, hi]."""
    delta = base * pct * (random.random() * 2 - 1)
    return round(max(lo, min(hi, base + delta)), 2)


def _evaluate(cpu: float, packet_loss: float, latency: float):
    """Return (status, severity, breaches) based on threshold rules."""
    status   = "HEALTHY"
    severity = "NONE"
    breaches = []

    checks = [
        ("CPU Utilization", cpu,         "cpu"),
        ("Packet Loss",     packet_loss, "packet_loss"),
        ("Latency",         latency,     "latency"),
    ]
    for label, val, key in checks:
        if val > THRESHOLDS[key]["critical"]:
            breaches.append(
                f"{label} at {val} exceeds CRITICAL threshold ({THRESHOLDS[key]['critical']})"
            )
            status   = "CRITICAL"
            severity = "CRITICAL"
        elif val > THRESHOLDS[key]["warning"]:
            breaches.append(
                f"{label} at {val} exceeds WARNING threshold ({THRESHOLDS[key]['warning']})"
            )
            if status != "CRITICAL":
                status   = "DEGRADED"
                severity = "WARNING"

    return status, severity, breaches


async def fetch_metrics_node(state: dict) -> dict:
    """Read base metrics from DB, apply per-scan jitter, then evaluate health."""
    timestamp = datetime.now(timezone.utc).isoformat()
    device_reports: list[dict] = []
    alerts:         list[dict] = []

    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(NetworkDevice).where(NetworkDevice.name.in_(MONITORED_DEVICES))
            )
        ).scalars().all()
    db_map = {r.name: r for r in rows}

    for name in MONITORED_DEVICES:
        dev = db_map.get(name)
        if dev:
            # Apply ±20 % jitter so every scan shows different live values
            cpu         = _jitter(dev.cpu_pct,        pct=0.20, lo=0.0,  hi=100.0)
            packet_loss = _jitter(dev.packet_loss_pct, pct=0.30, lo=0.0,  hi=100.0)
            latency     = _jitter(dev.latency_ms,      pct=0.25, lo=1.0,  hi=500.0)
        else:
            cpu         = round(random.uniform(10, 100), 2)
            packet_loss = round(random.uniform(0,   10), 2)
            latency     = round(random.uniform(5,  500), 2)

        status, severity, breaches = _evaluate(cpu, packet_loss, latency)

        report = {
            "device": name,
            "status": status,
            "metrics": {
                "cpu":         f"{cpu}%",
                "packet_loss": f"{packet_loss}%",
                "latency":     f"{latency}ms",
            },
            "alert": {
                "raised":         bool(breaches),
                "severity":       severity,
                "reason":         "; ".join(breaches) if breaches else "All metrics normal",
                "timestamp":      timestamp,
                "root_cause":     "",
                "recommendation": "",
            },
        }
        device_reports.append(report)
        if breaches:
            alerts.append(report)

    return {"device_reports": device_reports, "alerts": alerts}


def _parse_llm_json(text: str) -> list:
    """Extract a JSON array from LLM output, tolerating markdown fences and prose."""
    # Try direct parse first
    try:
        return json.loads(text.strip())
    except Exception:
        pass
    # Strip markdown fences
    fenced = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(fenced)
    except Exception:
        pass
    # Pull out the first [...] block found anywhere in the response
    match = re.search(r"\[.*?\]", fenced, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return []


async def analyze_alerts_node(state: dict) -> dict:
    """Call LLM for root-cause analysis and recommendations on every alerted device."""
    alerts         = state.get("alerts", [])
    device_reports = state.get("device_reports", [])

    alert_blocks = []
    for a in alerts:
        m = a["metrics"]
        alert_blocks.append(
            f"Device : {a['device']}\n"
            f"Status : {a['status']}\n"
            f"Metrics: CPU={m['cpu']}, Packet Loss={m['packet_loss']}, Latency={m['latency']}\n"
            f"Breach : {a['alert']['reason']}"
        )

    system = SystemMessage(content=(
        "You are a Senior Telecom Network Operations engineer.\n"
        "For each alerted device give:\n"
        "  root_cause     — the most likely technical cause (2-3 sentences, be specific)\n"
        "  recommendation — exact remediation steps an NOC engineer should take (2-3 sentences)\n"
        "  reasoning      — why you concluded this root cause (1-2 sentences)\n\n"
        "Output ONLY a raw JSON array with no extra text, one object per device:\n"
        '[{"device":"...","root_cause":"...","recommendation":"...","reasoning":"..."}]'
    ))
    human = HumanMessage(
        content="Analyze these live network alerts:\n\n" + "\n\n".join(alert_blocks)
    )

    response = await llm.ainvoke([system, human])
    analyses = _parse_llm_json(response.content)
    analysis_map = {a["device"]: a for a in analyses if isinstance(a, dict)}

    for report in device_reports:
        if report["alert"]["raised"]:
            ana = analysis_map.get(report["device"], {})
            report["alert"]["root_cause"]     = ana.get("root_cause",     "Analysis unavailable")
            report["alert"]["recommendation"] = ana.get("recommendation", "Manual investigation required")
            report["alert"]["reasoning"]      = ana.get("reasoning",      "")

    critical = sum(1 for r in device_reports if r["status"] == "CRITICAL")
    degraded = sum(1 for r in device_reports if r["status"] == "DEGRADED")
    healthy  = sum(1 for r in device_reports if r["status"] == "HEALTHY")

    result = {
        "summary": {
            "total_devices": len(device_reports),
            "critical":      critical,
            "degraded":      degraded,
            "healthy":       healthy,
            "alerts_raised": len(alerts),
        },
        "device_reports": device_reports,
    }
    return {"result": result, "status": "completed", "messages": [response]}


def should_analyze(state: dict) -> str:
    return "analyze" if state.get("alerts") else "end"
