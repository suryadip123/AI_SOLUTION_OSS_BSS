import json
import re
import random
from datetime import datetime, timezone
from sqlalchemy import select
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base_agent import get_llm
from app.db.database import AsyncSessionLocal
from app.db.models.call import CallGateway
from app.agents.call.tools import THRESHOLDS

llm = get_llm()


def _random_metrics() -> dict:
    """Generate call-analytics metrics with ~60% healthy / 25% warning / 15% critical split.

    Tier boundaries derived from THRESHOLDS:
      call_success_rate : warn<95%,   crit<90%   (below = worse)
      call_drop_rate    : warn>3%,    crit>7%    (above = worse)
      avg_duration_min  : warn<2min,  crit<1min  (below = worse — very short = abnormal drops)
    """
    tier = random.choices(
        population=["healthy", "warning", "critical"],
        weights=[0.60, 0.25, 0.15],
        k=1,
    )[0]

    if tier == "healthy":
        success  = round(random.uniform(95.0, 100.0), 2)
        drop     = round(random.uniform(0.0,    2.9), 2)
        duration = round(random.uniform(2.0,   10.0), 2)
    elif tier == "warning":
        success  = round(random.uniform(90.0,  94.9), 2)
        drop     = round(random.uniform(3.0,    6.9), 2)
        duration = round(random.uniform(1.0,    1.99), 2)
    else:  # critical
        success  = round(random.uniform(70.0,  89.9), 2)
        drop     = round(random.uniform(7.0,   20.0), 2)
        duration = round(random.uniform(0.1,    0.99), 2)

    return {
        "call_success_rate": success,
        "call_drop_rate":    drop,
        "avg_duration_min":  duration,
    }


def _severity(success: float, drop: float, duration: float):
    """Return (status, severity, breaches) for a call gateway."""
    status   = "HEALTHY"
    severity = "NONE"
    breaches = []

    checks = [
        ("Call Success Rate", success,  "call_success_rate"),
        ("Call Drop Rate",    drop,     "call_drop_rate"),
        ("Avg Duration",      duration, "avg_duration_min"),
    ]
    for label, val, key in checks:
        cfg   = THRESHOLDS[key]
        below = cfg["direction"] == "below"
        unit  = "%" if key != "avg_duration_min" else "min"
        if (below and val < cfg["critical"]) or (not below and val > cfg["critical"]):
            breaches.append(
                f"{label} at {val}{unit} breaches CRITICAL ({cfg['critical']}{unit})"
            )
            status   = "CRITICAL"
            severity = "CRITICAL"
        elif (below and val < cfg["warning"]) or (not below and val > cfg["warning"]):
            breaches.append(
                f"{label} at {val}{unit} breaches WARNING ({cfg['warning']}{unit})"
            )
            if status != "CRITICAL":
                status   = "DEGRADED"
                severity = "WARNING"

    return status, severity, breaches


async def fetch_metrics_node(state: dict) -> dict:
    """Generate randomized metrics (~60% healthy / 25% warning / 15% critical) per gateway.

    Gateway profile data (region, total_calls) is read from the DB for context;
    live call KPIs are generated probabilistically on every run.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(CallGateway))).scalars().all()

    reports: list[dict] = []
    alerts:  list[dict] = []

    for gw in rows:
        # ── Probabilistic metric generation ─────────────────────────────────
        m        = _random_metrics()
        success  = m["call_success_rate"]
        drop     = m["call_drop_rate"]
        duration = m["avg_duration_min"]

        status, severity, breaches = _severity(success, drop, duration)

        report = {
            "gateway_id":  gw.gateway_id,
            "region":      gw.region,
            "total_calls": gw.total_calls,
            "status":      status,
            "metrics": {
                "success_rate": f"{success}%",
                "drop_rate":    f"{drop}%",
                "avg_duration": f"{duration}min",
            },
            "alert": {
                "raised":         bool(breaches),
                "severity":       severity,
                "reason":         "; ".join(breaches) if breaches else "All call metrics normal",
                "timestamp":      timestamp,
                "root_cause":     "",
                "recommendation": "",
                "reasoning":      "",
            },
        }
        reports.append(report)
        if breaches:
            alerts.append(report)

    return {"call_reports": reports, "alerts": alerts}


def _parse_llm_json(text: str) -> list:
    """Extract a JSON array from LLM output, tolerating markdown fences and prose."""
    try:
        return json.loads(text.strip())
    except Exception:
        pass
    fenced = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(fenced)
    except Exception:
        pass
    match = re.search(r"\[.*?\]", fenced, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return []


async def analyze_alerts_node(state: dict) -> dict:
    """Call LLM for root-cause analysis on degraded / critical call gateways."""
    alerts  = state.get("alerts", [])
    reports = state.get("call_reports", [])

    rank    = {"CRITICAL": 4, "WARNING": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0}
    top     = sorted(alerts, key=lambda r: rank.get(r["alert"]["severity"], 0), reverse=True)[:3]
    skipped = {r["gateway_id"] for r in alerts if r not in top}

    blocks = [
        f"Gateway : {r['gateway_id']} (Region: {r['region']}, Calls: {r['total_calls']})\n"
        f"Status  : {r['status']}\n"
        f"Metrics : Success={r['metrics']['success_rate']}, "
        f"Drop={r['metrics']['drop_rate']}, Duration={r['metrics']['avg_duration']}\n"
        f"Breach  : {r['alert']['reason']}"
        for r in top
    ]

    system = SystemMessage(content=(
        "You are a Senior Telecom Call Operations engineer.\n"
        "For each degraded or critical call gateway provide:\n"
        "  root_cause     — the most likely technical cause (2-3 sentences)\n"
        "  recommendation — exact remediation steps the NOC team should take (2-3 sentences)\n"
        "  reasoning      — why you concluded this root cause (1-2 sentences)\n\n"
        "Output ONLY a raw JSON array, one object per gateway:\n"
        '[{"gateway_id":"...","root_cause":"...","recommendation":"...","reasoning":"..."}]'
    ))
    human = HumanMessage(
        content="Analyze these call gateway alerts:\n\n" + "\n\n".join(blocks)
    )

    response = await llm.ainvoke([system, human])
    analyses = _parse_llm_json(response.content)
    amap     = {a["gateway_id"]: a for a in analyses if isinstance(a, dict)}

    for r in reports:
        if r["alert"]["raised"]:
            if r["gateway_id"] in skipped:
                r["alert"]["recommendation"] = (
                    "Queued — lower priority than current critical alerts"
                )
            else:
                ana = amap.get(r["gateway_id"], {})
                r["alert"]["root_cause"]     = ana.get("root_cause",     "Analysis unavailable")
                r["alert"]["recommendation"] = ana.get("recommendation", "Manual investigation required")
                r["alert"]["reasoning"]      = ana.get("reasoning",      "")

    critical = sum(1 for r in reports if r["status"] == "CRITICAL")
    degraded = sum(1 for r in reports if r["status"] == "DEGRADED")
    healthy  = sum(1 for r in reports if r["status"] == "HEALTHY")

    result = {
        "summary": {
            "total_gateways": len(reports),
            "critical":       critical,
            "degraded":       degraded,
            "healthy":        healthy,
            "alerts_raised":  len(alerts),
        },
        "call_reports": reports,
    }
    return {"result": result, "status": "completed", "messages": [response]}


def should_analyze(state: dict) -> str:
    return "analyze" if state.get("alerts") else "end"
