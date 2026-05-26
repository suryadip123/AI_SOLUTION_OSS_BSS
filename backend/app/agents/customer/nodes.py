import json
import re
import random
from datetime import datetime, timezone
from sqlalchemy import select
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base_agent import get_llm
from app.db.database import AsyncSessionLocal
from app.db.models.customer import CustomerAccount
from app.agents.customer.tools import MONITORED_ACCOUNTS, THRESHOLDS

llm = get_llm()


def _jitter(base: float, pct: float = 0.15, lo: float = 0.0, hi: float = 100.0) -> float:
    """Apply ±pct random variation around base, clamped to [lo, hi]."""
    delta = base * pct * (random.random() * 2 - 1)
    return round(max(lo, min(hi, base + delta)), 2)


def _evaluate(completion: float, fulfillment: float, sla_breach: float):
    """Return (status, severity, breaches) for a customer account."""
    status   = "HEALTHY"
    severity = "NONE"
    breaches = []

    checks = [
        ("Order Completion Rate", completion, "order_completion_rate"),
        ("Avg Fulfillment Time",  fulfillment, "avg_fulfillment_time"),
        ("SLA Breach Rate",       sla_breach,  "sla_breach_rate"),
    ]
    for label, val, key in checks:
        cfg = THRESHOLDS[key]
        is_below = cfg["direction"] == "below"
        if (is_below and val < cfg["critical"]) or (not is_below and val > cfg["critical"]):
            unit = "%" if key != "avg_fulfillment_time" else "h"
            breaches.append(
                f"{label} at {val}{unit} breaches CRITICAL threshold ({cfg['critical']}{unit})"
            )
            status   = "CRITICAL"
            severity = "CRITICAL"
        elif (is_below and val < cfg["warning"]) or (not is_below and val > cfg["warning"]):
            unit = "%" if key != "avg_fulfillment_time" else "h"
            breaches.append(
                f"{label} at {val}{unit} breaches WARNING threshold ({cfg['warning']}{unit})"
            )
            if status != "CRITICAL":
                status   = "AT_RISK"
                severity = "WARNING"

    return status, severity, breaches


async def fetch_metrics_node(state: dict) -> dict:
    """Read base metrics from DB, apply per-scan jitter, evaluate health."""
    timestamp = datetime.now(timezone.utc).isoformat()
    customer_reports: list[dict] = []
    alerts:           list[dict] = []

    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(CustomerAccount).where(CustomerAccount.account_id.in_(MONITORED_ACCOUNTS))
            )
        ).scalars().all()
    db_map = {r.account_id: r for r in rows}

    for acc_id in MONITORED_ACCOUNTS:
        acc = db_map.get(acc_id)
        if acc:
            completion  = _jitter(acc.order_completion_rate, pct=0.08, lo=0.0,  hi=100.0)
            fulfillment = _jitter(acc.avg_fulfillment_time,  pct=0.15, lo=1.0,  hi=200.0)
            sla_breach  = _jitter(acc.sla_breach_rate,       pct=0.20, lo=0.0,  hi=100.0)
            name        = acc.name
            segment     = acc.segment
            region      = acc.region
            plan        = acc.plan
            active_ord  = acc.active_orders
        else:
            completion  = round(random.uniform(60, 100), 2)
            fulfillment = round(random.uniform(10, 100), 2)
            sla_breach  = round(random.uniform(0,   25), 2)
            name        = acc_id
            segment     = "Unknown"
            region      = "—"
            plan        = "—"
            active_ord  = 0

        status, severity, breaches = _evaluate(completion, fulfillment, sla_breach)

        report = {
            "account_id":   acc_id,
            "name":         name,
            "segment":      segment,
            "region":       region,
            "plan":         plan,
            "active_orders": active_ord,
            "status":       status,
            "metrics": {
                "order_completion_rate": f"{completion}%",
                "avg_fulfillment_time":  f"{fulfillment}h",
                "sla_breach_rate":       f"{sla_breach}%",
            },
            "alert": {
                "raised":         bool(breaches),
                "severity":       severity,
                "reason":         "; ".join(breaches) if breaches else "All metrics within SLA",
                "timestamp":      timestamp,
                "root_cause":     "",
                "recommendation": "",
                "reasoning":      "",
            },
        }
        customer_reports.append(report)
        if breaches:
            alerts.append(report)

    return {"customer_reports": customer_reports, "alerts": alerts}


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
    """Call LLM for root-cause analysis and recommendations on alerted accounts."""
    alerts           = state.get("alerts", [])
    customer_reports = state.get("customer_reports", [])

    alert_blocks = []
    for a in alerts:
        m = a["metrics"]
        alert_blocks.append(
            f"Account : {a['account_id']} — {a['name']} ({a['segment']}, {a['plan']} plan)\n"
            f"Status  : {a['status']}\n"
            f"Metrics : Completion={m['order_completion_rate']}, "
            f"Fulfillment={m['avg_fulfillment_time']}, SLA Breach={m['sla_breach_rate']}\n"
            f"Breach  : {a['alert']['reason']}"
        )

    system = SystemMessage(content=(
        "You are a Senior Telecom Customer Operations analyst.\n"
        "For each at-risk or critical customer account provide:\n"
        "  root_cause     — the most likely business/technical cause (2-3 sentences)\n"
        "  recommendation — specific corrective actions the operations team should take (2-3 sentences)\n"
        "  reasoning      — why you concluded this root cause (1-2 sentences)\n\n"
        "Output ONLY a raw JSON array, one object per account:\n"
        '[{"account_id":"...","root_cause":"...","recommendation":"...","reasoning":"..."}]'
    ))
    human = HumanMessage(
        content="Analyze these customer order health alerts:\n\n" + "\n\n".join(alert_blocks)
    )

    response = await llm.ainvoke([system, human])
    analyses = _parse_llm_json(response.content)
    analysis_map = {a["account_id"]: a for a in analyses if isinstance(a, dict)}

    for report in customer_reports:
        if report["alert"]["raised"]:
            ana = analysis_map.get(report["account_id"], {})
            report["alert"]["root_cause"]     = ana.get("root_cause",     "Analysis unavailable")
            report["alert"]["recommendation"] = ana.get("recommendation", "Manual investigation required")
            report["alert"]["reasoning"]      = ana.get("reasoning",      "")

    critical = sum(1 for r in customer_reports if r["status"] == "CRITICAL")
    at_risk  = sum(1 for r in customer_reports if r["status"] == "AT_RISK")
    healthy  = sum(1 for r in customer_reports if r["status"] == "HEALTHY")

    result = {
        "summary": {
            "total_accounts": len(customer_reports),
            "critical":       critical,
            "at_risk":        at_risk,
            "healthy":        healthy,
            "alerts_raised":  len(alerts),
        },
        "customer_reports": customer_reports,
    }
    return {"result": result, "status": "completed", "messages": [response]}


def should_analyze(state: dict) -> str:
    return "analyze" if state.get("alerts") else "end"
