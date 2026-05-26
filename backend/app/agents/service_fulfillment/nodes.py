import json
import re
import random
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base_agent import get_llm
from app.db.database import AsyncSessionLocal
from app.db.models.service_fulfillment import ServiceOrder, ProvisioningStep, StepMetrics
from app.agents.service_fulfillment.tools import SLA_HOURS, STEP_BASELINE_SECONDS, ALERT_TYPES

llm = get_llm()

AT_RISK_PCT  = 0.80   # 80 % of SLA elapsed → AT_RISK
DELAY_FACTOR = 2.0    # current step running > 2× baseline → FULFILLMENT_DELAY


def _jitter(value: float, pct: float = 0.03) -> float:
    return round(value * (1 + pct * (random.random() * 2 - 1)), 2)


def _sla_status(elapsed_pct: float) -> str:
    if elapsed_pct >= 100: return "BREACHED"
    if elapsed_pct >= 80:  return "AT_RISK"
    return "ON_TRACK"


async def fetch_orders_node(state: dict) -> dict:
    """Read active orders + steps from DB, evaluate SLA and step health, build alert list."""
    now       = datetime.utcnow()
    timestamp = datetime.now(timezone.utc).isoformat()

    async with AsyncSessionLocal() as db:
        orders = (await db.execute(
            select(ServiceOrder).where(ServiceOrder.status != "COMPLETED")
        )).scalars().all()

        step_rows = (await db.execute(select(ProvisioningStep))).scalars().all()
        metrics   = (await db.execute(select(StepMetrics))).scalars().all()

    steps_by_order = {}
    for s in step_rows:
        steps_by_order.setdefault(s.order_id, []).append(s)

    baseline = {m.step_name: m.avg_duration_seconds for m in metrics}
    # Fall back to hardcoded if DB baseline missing
    for k, v in STEP_BASELINE_SECONDS.items():
        baseline.setdefault(k, v)

    order_reports: list[dict] = []
    alerts:        list[dict] = []

    for order in orders:
        sla_h        = SLA_HOURS.get(order.order_type, 24)
        created_utc  = order.created_at  # stored as naive UTC
        elapsed_h    = (now - created_utc).total_seconds() / 3600
        elapsed_h    = _jitter(elapsed_h, pct=0.03)          # ±3 % measurement noise
        elapsed_pct  = round((elapsed_h / sla_h) * 100, 1)
        sla_st       = _sla_status(elapsed_pct)

        # Build step summary
        order_steps = sorted(steps_by_order.get(order.id, []), key=lambda s: s.id)
        step_summary = []
        for s in order_steps:
            dur = None
            if s.status == "RUNNING" and s.start_time:
                dur = round((now - s.start_time).total_seconds(), 1)
            elif s.duration_seconds is not None:
                dur = s.duration_seconds
            step_summary.append({
                "step":     s.step_name,
                "status":   s.status,
                "duration": f"{dur}s" if dur is not None else None,
                "error":    s.error_message,
            })

        # Detect alerts
        order_alerts = []

        if sla_st == "BREACHED":
            order_alerts.append({
                "type":     "SLA_BREACH",
                "severity": "CRITICAL",
                "reason":   f"Order {order.id} SLA breached — {elapsed_pct}% of {sla_h}h elapsed",
            })
        elif sla_st == "AT_RISK":
            order_alerts.append({
                "type":     "SLA_AT_RISK",
                "severity": "HIGH",
                "reason":   f"Order {order.id} approaching SLA deadline — {elapsed_pct}% of {sla_h}h elapsed",
            })

        if order.status == "FAILED":
            order_alerts.append({
                "type":     "STEP_FAILURE",
                "severity": "HIGH",
                "reason":   f"Step '{order.current_step}' failed: {order.failure_reason or 'Unknown error'}",
            })

        # Check running step for delay
        for s in order_steps:
            if s.status == "RUNNING" and s.start_time:
                running_sec = (now - s.start_time).total_seconds()
                base_sec    = baseline.get(s.step_name, 60)
                if running_sec > DELAY_FACTOR * base_sec:
                    order_alerts.append({
                        "type":     "FULFILLMENT_DELAY",
                        "severity": "MEDIUM",
                        "reason":   (
                            f"Step '{s.step_name}' running for {round(running_sec)}s — "
                            f"{round(running_sec/base_sec, 1)}× average ({base_sec}s)"
                        ),
                    })

        overall_severity = "NONE"
        for a in order_alerts:
            rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0}
            if rank.get(a["severity"], 0) > rank.get(overall_severity, 0):
                overall_severity = a["severity"]

        report = {
            "order_id":      order.id,
            "order_type":    order.order_type,
            "customer_id":   order.customer_id,
            "customer_name": order.customer_name,
            "status":        order.status,
            "sla_status":    sla_st,
            "current_step":  order.current_step,
            "metrics": {
                "elapsed_hours":  f"{round(elapsed_h, 2)}h",
                "sla_hours":      f"{sla_h}h",
                "elapsed_pct":    f"{elapsed_pct}%",
            },
            "steps": step_summary,
            "alert": {
                "raised":         bool(order_alerts),
                "severity":       overall_severity,
                "alerts":         order_alerts,
                "timestamp":      timestamp,
                "rca":            {},
                "recommendation": "",
                "reasoning":      "",
                "is_ambiguous":   False,
            },
        }
        order_reports.append(report)
        if order_alerts:
            alerts.append(report)

    return {"order_reports": order_reports, "alerts": alerts}


def _parse_llm_json(text: str) -> list:
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


async def analyze_rca_node(state: dict) -> dict:
    """Call LLM to produce WHAT/WHY/IMPACT/FIX/PREVENTION RCA for each alerted order.
    To keep response time reasonable, only the top 4 highest-severity orders are sent to the LLM."""
    alerts        = state.get("alerts", [])
    order_reports = state.get("order_reports", [])

    # Rank and cap: CRITICAL > HIGH > MEDIUM, max 4 to LLM
    severity_rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0}
    alerts_sorted = sorted(alerts, key=lambda r: severity_rank.get(r["alert"]["severity"], 0), reverse=True)
    llm_alerts    = alerts_sorted[:4]
    skipped_ids   = {r["order_id"] for r in alerts_sorted[4:]}

    alert_blocks = []
    for r in llm_alerts:
        m      = r["metrics"]
        steps  = r["steps"]
        a_list = r["alert"]["alerts"]
        step_log = "; ".join(
            f"{s['step']}={s['status']}" + (f"({s['duration']})" if s['duration'] else "")
            + (f"[ERR:{s['error']}]" if s['error'] else "")
            for s in steps
        )
        alert_log = " | ".join(a["reason"] for a in a_list)
        alert_blocks.append(
            f"Order    : {r['order_id']} ({r['order_type']}) — Customer: {r['customer_name']}\n"
            f"Status   : {r['status']} | SLA: {r['sla_status']} ({m['elapsed_pct']} of {m['sla_hours']})\n"
            f"Steps    : {step_log}\n"
            f"Alerts   : {alert_log}"
        )

    system = SystemMessage(content=(
        "You are a Senior Telecom Service Fulfillment engineer.\n"
        "For each order alert, produce a structured analysis. "
        "If the root cause is unclear or conflicting, set is_ambiguous to true.\n\n"
        "Output ONLY a raw JSON array, one object per order:\n"
        "[\n"
        "  {\n"
        '    "order_id": "...",\n'
        '    "rca": {\n'
        '      "what": "One-line description of what happened",\n'
        '      "why": "Chain of cause leading to this failure",\n'
        '      "impact": "Affected customer / services / downstream orders",\n'
        '      "fix": "Exact resolution steps for the NOC team",\n'
        '      "prevention": "How to prevent recurrence"\n'
        "    },\n"
        '    "recommendation": "Immediate next action (e.g. re-trigger step, escalate to NOC)",\n'
        '    "reasoning": "Why you concluded this root cause",\n'
        '    "is_ambiguous": false\n'
        "  }\n"
        "]"
    ))
    human = HumanMessage(
        content="Analyze these service fulfillment alerts:\n\n" + "\n\n".join(alert_blocks)
    )

    response  = await llm.ainvoke([system, human])
    analyses  = _parse_llm_json(response.content)
    analy_map = {a["order_id"]: a for a in analyses if isinstance(a, dict)}

    for report in order_reports:
        if report["alert"]["raised"]:
            if report["order_id"] in skipped_ids:
                report["alert"]["recommendation"] = "Queued for analysis — lower priority than current critical alerts"
            else:
                ana = analy_map.get(report["order_id"], {})
                report["alert"]["rca"]            = ana.get("rca", {})
                report["alert"]["recommendation"] = ana.get("recommendation", "Manual investigation required")
                report["alert"]["reasoning"]      = ana.get("reasoning", "")
                report["alert"]["is_ambiguous"]   = ana.get("is_ambiguous", False)

    breached  = sum(1 for r in order_reports if r["sla_status"] == "BREACHED")
    at_risk   = sum(1 for r in order_reports if r["sla_status"] == "AT_RISK")
    on_track  = sum(1 for r in order_reports if r["sla_status"] == "ON_TRACK")
    failed    = sum(1 for r in order_reports if r["status"] == "FAILED")

    result = {
        "summary": {
            "total_orders":  len(order_reports),
            "on_track":      on_track,
            "at_risk":       at_risk,
            "breached":      breached,
            "failed":        failed,
            "alerts_raised": len(alerts),
        },
        "order_reports": order_reports,
    }
    return {"result": result, "status": "completed", "messages": [response]}


def should_analyze(state: dict) -> str:
    return "analyze" if state.get("alerts") else "end"
