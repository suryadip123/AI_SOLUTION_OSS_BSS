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


def _random_metrics() -> dict:
    """Generate customer metrics with ~60% healthy / 25% warning / 15% critical split.

    Tier boundaries are derived directly from THRESHOLDS:
      order_completion_rate: warn<85, crit<70  (below = worse)
      avg_fulfillment_time : warn>48h, crit>72h (above = worse)
      sla_breach_rate      : warn>5%,  crit>15% (above = worse)
    """
    tier = random.choices(
        population=["healthy", "warning", "critical"],
        weights=[0.60, 0.25, 0.15],
        k=1,
    )[0]

    if tier == "healthy":
        completion  = round(random.uniform(85.0, 100.0), 2)
        fulfillment = round(random.uniform(1.0,   47.9), 2)
        sla_breach  = round(random.uniform(0.0,    4.9), 2)
    elif tier == "warning":
        completion  = round(random.uniform(70.0,  84.9), 2)
        fulfillment = round(random.uniform(48.0,  71.9), 2)
        sla_breach  = round(random.uniform(5.0,   14.9), 2)
    else:  # critical
        completion  = round(random.uniform(35.0,  69.9), 2)
        fulfillment = round(random.uniform(72.0, 160.0), 2)
        sla_breach  = round(random.uniform(15.0,  45.0), 2)

    return {
        "order_completion_rate": completion,
        "avg_fulfillment_time":  fulfillment,
        "sla_breach_rate":       sla_breach,
    }


def _severity(completion: float, fulfillment: float, sla_breach: float):
    """Return (status, severity, breaches) for a customer account."""
    status   = "HEALTHY"
    severity = "NONE"
    breaches = []

    checks = [
        ("Order Completion Rate", completion,  "order_completion_rate"),
        ("Avg Fulfillment Time",  fulfillment, "avg_fulfillment_time"),
        ("SLA Breach Rate",       sla_breach,  "sla_breach_rate"),
    ]
    for label, val, key in checks:
        cfg      = THRESHOLDS[key]
        is_below = cfg["direction"] == "below"
        unit     = "%" if key != "avg_fulfillment_time" else "h"
        if (is_below and val < cfg["critical"]) or (not is_below and val > cfg["critical"]):
            breaches.append(
                f"{label} at {val}{unit} breaches CRITICAL threshold ({cfg['critical']}{unit})"
            )
            status   = "CRITICAL"
            severity = "CRITICAL"
        elif (is_below and val < cfg["warning"]) or (not is_below and val > cfg["warning"]):
            breaches.append(
                f"{label} at {val}{unit} breaches WARNING threshold ({cfg['warning']}{unit})"
            )
            if status != "CRITICAL":
                status   = "AT_RISK"
                severity = "WARNING"

    return status, severity, breaches


async def fetch_metrics_node(state: dict) -> dict:
    """Generate randomized metrics (~60% healthy / 25% warning / 15% critical) per account.

    Profile data (name, segment, region, plan) is still read from the DB so the
    reports stay contextually meaningful.  Only the live metric values are
    generated probabilistically — this guarantees the intended health distribution
    on every agent run instead of always reflecting the seeded-DB baseline.
    """
    timestamp        = datetime.now(timezone.utc).isoformat()
    customer_reports: list[dict] = []
    alerts:           list[dict] = []

    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(CustomerAccount).where(
                    CustomerAccount.account_id.in_(MONITORED_ACCOUNTS)
                )
            )
        ).scalars().all()
    db_map = {r.account_id: r for r in rows}

    for acc_id in MONITORED_ACCOUNTS:
        acc = db_map.get(acc_id)

        # ── Probabilistic metric generation ─────────────────────────────────
        m           = _random_metrics()
        completion  = m["order_completion_rate"]
        fulfillment = m["avg_fulfillment_time"]
        sla_breach  = m["sla_breach_rate"]

        # ── Profile data from DB (fallback to safe defaults) ────────────────
        name       = acc.name          if acc else acc_id
        segment    = acc.segment       if acc else "Unknown"
        region     = acc.region        if acc else "—"
        plan       = acc.plan          if acc else "—"
        active_ord = acc.active_orders if acc else 0

        status, severity, breaches = _severity(completion, fulfillment, sla_breach)

        report = {
            "account_id":    acc_id,
            "name":          name,
            "segment":       segment,
            "region":        region,
            "plan":          plan,
            "active_orders": active_ord,
            "status":        status,
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
