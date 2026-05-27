import json
import re
import random
from datetime import datetime, timezone
from sqlalchemy import select
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base_agent import get_llm
from app.db.database import AsyncSessionLocal
from app.db.models.billing import BillingAccount
from app.agents.billing.tools import THRESHOLDS

llm = get_llm()


def _random_metrics() -> dict:
    """Generate billing metrics with ~60% healthy / 25% warning / 15% critical split.

    Tier boundaries derived from THRESHOLDS:
      bill_gen_success_rate   : warn<95%,  crit<85%  (below = worse)
      payment_collection_rate : warn<90%,  crit<75%  (below = worse)
      dispute_rate            : warn>3%,   crit>8%   (above = worse)
    """
    tier = random.choices(
        population=["healthy", "warning", "critical"],
        weights=[0.60, 0.25, 0.15],
        k=1,
    )[0]

    if tier == "healthy":
        gen     = round(random.uniform(95.0, 100.0), 2)
        pay     = round(random.uniform(90.0, 100.0), 2)
        dispute = round(random.uniform(0.0,    2.9), 2)
    elif tier == "warning":
        gen     = round(random.uniform(85.0,  94.9), 2)
        pay     = round(random.uniform(75.0,  89.9), 2)
        dispute = round(random.uniform(3.0,    7.9), 2)
    else:  # critical
        gen     = round(random.uniform(50.0,  84.9), 2)
        pay     = round(random.uniform(40.0,  74.9), 2)
        dispute = round(random.uniform(8.0,   25.0), 2)

    return {
        "bill_gen_success_rate":   gen,
        "payment_collection_rate": pay,
        "dispute_rate":            dispute,
    }


def _severity(gen: float, pay: float, dispute: float):
    """Return (status, severity, breaches) for a billing account."""
    status   = "HEALTHY"
    severity = "NONE"
    breaches = []

    checks = [
        ("Bill Gen Rate",   gen,     "bill_gen_success_rate"),
        ("Payment Rate",    pay,     "payment_collection_rate"),
        ("Dispute Rate",    dispute, "dispute_rate"),
    ]
    for label, val, key in checks:
        cfg   = THRESHOLDS[key]
        below = cfg["direction"] == "below"
        if (below and val < cfg["critical"]) or (not below and val > cfg["critical"]):
            breaches.append(
                f"{label} at {val}% breaches CRITICAL ({cfg['critical']}%)"
            )
            status   = "CRITICAL"
            severity = "CRITICAL"
        elif (below and val < cfg["warning"]) or (not below and val > cfg["warning"]):
            breaches.append(
                f"{label} at {val}% breaches WARNING ({cfg['warning']}%)"
            )
            if status != "CRITICAL":
                status   = "AT_RISK"
                severity = "WARNING"

    return status, severity, breaches


async def fetch_metrics_node(state: dict) -> dict:
    """Generate randomized metrics (~60% healthy / 25% warning / 15% critical) per account.

    Account profile data (name, segment, region, total_bills) is read from the DB;
    live billing KPIs are generated probabilistically on every run.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(BillingAccount))).scalars().all()

    reports: list[dict] = []
    alerts:  list[dict] = []

    for acc in rows:
        # ── Probabilistic metric generation ─────────────────────────────────
        m       = _random_metrics()
        gen     = m["bill_gen_success_rate"]
        pay     = m["payment_collection_rate"]
        dispute = m["dispute_rate"]

        status, severity, breaches = _severity(gen, pay, dispute)

        report = {
            "account_id":  acc.account_id,
            "name":        acc.name,
            "segment":     acc.segment,
            "region":      acc.region,
            "total_bills": acc.total_bills,
            "status":      status,
            "metrics": {
                "bill_gen_rate":  f"{gen}%",
                "payment_rate":   f"{pay}%",
                "dispute_rate":   f"{dispute}%",
            },
            "alert": {
                "raised":         bool(breaches),
                "severity":       severity,
                "reason":         "; ".join(breaches) if breaches else "All billing metrics normal",
                "timestamp":      timestamp,
                "root_cause":     "",
                "recommendation": "",
                "reasoning":      "",
            },
        }
        reports.append(report)
        if breaches:
            alerts.append(report)

    return {"billing_reports": reports, "alerts": alerts}


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
    """Call LLM for root-cause analysis on at-risk / critical billing accounts."""
    alerts  = state.get("alerts", [])
    reports = state.get("billing_reports", [])

    rank    = {"CRITICAL": 4, "WARNING": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0}
    top     = sorted(alerts, key=lambda r: rank.get(r["alert"]["severity"], 0), reverse=True)[:3]
    skipped = {r["account_id"] for r in alerts if r not in top}

    blocks = [
        f"Account : {r['account_id']} — {r['name']} ({r['segment']})\n"
        f"Status  : {r['status']}\n"
        f"Metrics : Gen={r['metrics']['bill_gen_rate']}, "
        f"Pay={r['metrics']['payment_rate']}, Dispute={r['metrics']['dispute_rate']}\n"
        f"Breach  : {r['alert']['reason']}"
        for r in top
    ]

    system = SystemMessage(content=(
        "You are a Senior Telecom Billing Operations analyst.\n"
        "For each at-risk or critical billing account provide:\n"
        "  root_cause     — the most likely business/technical cause (2-3 sentences)\n"
        "  recommendation — specific corrective actions the billing team should take (2-3 sentences)\n"
        "  reasoning      — why you concluded this root cause (1-2 sentences)\n\n"
        "Output ONLY a raw JSON array, one object per account:\n"
        '[{"account_id":"...","root_cause":"...","recommendation":"...","reasoning":"..."}]'
    ))
    human = HumanMessage(
        content="Analyze these billing health alerts:\n\n" + "\n\n".join(blocks)
    )

    response = await llm.ainvoke([system, human])
    analyses = _parse_llm_json(response.content)
    amap     = {a["account_id"]: a for a in analyses if isinstance(a, dict)}

    for r in reports:
        if r["alert"]["raised"]:
            if r["account_id"] in skipped:
                r["alert"]["recommendation"] = (
                    "Queued — lower priority than current critical alerts"
                )
            else:
                ana = amap.get(r["account_id"], {})
                r["alert"]["root_cause"]     = ana.get("root_cause",     "Analysis unavailable")
                r["alert"]["recommendation"] = ana.get("recommendation", "Manual investigation required")
                r["alert"]["reasoning"]      = ana.get("reasoning",      "")

    critical = sum(1 for r in reports if r["status"] == "CRITICAL")
    at_risk  = sum(1 for r in reports if r["status"] == "AT_RISK")
    healthy  = sum(1 for r in reports if r["status"] == "HEALTHY")

    result = {
        "summary": {
            "total_accounts": len(reports),
            "critical":       critical,
            "at_risk":        at_risk,
            "healthy":        healthy,
            "alerts_raised":  len(alerts),
        },
        "billing_reports": reports,
    }
    return {"result": result, "status": "completed", "messages": [response]}


def should_analyze(state: dict) -> str:
    return "analyze" if state.get("alerts") else "end"
