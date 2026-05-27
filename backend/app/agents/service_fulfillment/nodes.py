import json
import re
import random
from datetime import datetime, timezone
from sqlalchemy import select
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base_agent import get_llm
from app.db.database import AsyncSessionLocal
from app.db.models.service_fulfillment import ServiceOrder, ProvisioningStep, StepMetrics
from app.agents.service_fulfillment.tools import SLA_HOURS, STEP_BASELINE_SECONDS, ALERT_TYPES

llm = get_llm()

# Domain thresholds for the three headline fulfillment metrics
THRESHOLDS = {
    "provisioning_success_rate": {"warning": 90.0, "critical": 75.0, "direction": "below"},
    "order_backlog":             {"warning": 10.0, "critical": 25.0, "direction": "above"},
    "sla_breach_rate":           {"warning":  8.0, "critical": 20.0, "direction": "above"},
}

AT_RISK_PCT  = 80.0   # % of SLA elapsed → AT_RISK
DELAY_FACTOR = 2.0    # current step running > 2× baseline → FULFILLMENT_DELAY


def _random_metrics(sla_hours: int) -> dict:
    """Generate per-order fulfillment metrics with ~60% healthy / 25% warning / 15% critical.

    Tier boundaries:
      elapsed_pct          : <80 → ON_TRACK (healthy), 80-99 → AT_RISK (warning), ≥100 → BREACHED (critical)
      provisioning_success : >90% healthy, 75-90% warning, <75% critical
      order_backlog        : <10 healthy, 10-24 warning, ≥25 critical
      sla_breach_rate      : <8% healthy, 8-19% warning, ≥20% critical
    """
    tier = random.choices(
        population=["healthy", "warning", "critical"],
        weights=[0.60, 0.25, 0.15],
        k=1,
    )[0]

    if tier == "healthy":
        elapsed_pct   = round(random.uniform(5.0,  74.9), 1)
        prov_success  = round(random.uniform(90.1, 100.0), 2)
        order_backlog = random.randint(0, 9)
        sla_breach_rt = round(random.uniform(0.0,   7.9), 2)
    elif tier == "warning":
        elapsed_pct   = round(random.uniform(80.0,  97.9), 1)
        prov_success  = round(random.uniform(75.0,  89.9), 2)
        order_backlog = random.randint(10, 24)
        sla_breach_rt = round(random.uniform(8.0,  19.9), 2)
    else:  # critical
        elapsed_pct   = round(random.uniform(100.0, 150.0), 1)
        prov_success  = round(random.uniform(40.0,  74.9), 2)
        order_backlog = random.randint(25, 75)
        sla_breach_rt = round(random.uniform(20.0,  55.0), 2)

    elapsed_hours = round((elapsed_pct / 100.0) * sla_hours, 2)
    return {
        "elapsed_pct":               elapsed_pct,
        "elapsed_hours":             elapsed_hours,
        "provisioning_success_rate": prov_success,
        "order_backlog":             order_backlog,
        "sla_breach_rate":           sla_breach_rt,
    }


def _severity(
    elapsed_pct: float,
    prov_success: float,
    order_backlog: int,
    sla_breach_rate: float,
    order_id: str,
    sla_hours: int,
    order_status: str,
    failure_reason: str | None,
    current_step: str,
) -> tuple:
    """Return (sla_status, overall_severity, alert_list) for a service order."""
    rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0}
    order_alerts    = []
    overall_severity = "NONE"

    # ── SLA timing ──────────────────────────────────────────────────────────
    if elapsed_pct >= 100:
        sla_status = "BREACHED"
        order_alerts.append({
            "type":     "SLA_BREACH",
            "severity": "CRITICAL",
            "reason":   (
                f"Order {order_id} SLA breached — {elapsed_pct}% of {sla_hours}h elapsed"
            ),
        })
    elif elapsed_pct >= AT_RISK_PCT:
        sla_status = "AT_RISK"
        order_alerts.append({
            "type":     "SLA_AT_RISK",
            "severity": "HIGH",
            "reason":   (
                f"Order {order_id} approaching SLA deadline — {elapsed_pct}% of {sla_hours}h elapsed"
            ),
        })
    else:
        sla_status = "ON_TRACK"

    # ── Provisioning success rate ────────────────────────────────────────────
    if prov_success < THRESHOLDS["provisioning_success_rate"]["critical"]:
        order_alerts.append({
            "type":     "PROVISIONING_FAILURE",
            "severity": "CRITICAL",
            "reason":   (
                f"Provisioning success rate critically low at {prov_success}% "
                f"(threshold: {THRESHOLDS['provisioning_success_rate']['critical']}%)"
            ),
        })
    elif prov_success < THRESHOLDS["provisioning_success_rate"]["warning"]:
        order_alerts.append({
            "type":     "PROVISIONING_DEGRADED",
            "severity": "HIGH",
            "reason":   (
                f"Provisioning success rate degraded at {prov_success}% "
                f"(threshold: {THRESHOLDS['provisioning_success_rate']['warning']}%)"
            ),
        })

    # ── Order backlog ────────────────────────────────────────────────────────
    if order_backlog > THRESHOLDS["order_backlog"]["critical"]:
        order_alerts.append({
            "type":     "HIGH_BACKLOG",
            "severity": "CRITICAL",
            "reason":   (
                f"Order backlog critically high: {order_backlog} orders queued "
                f"(threshold: {int(THRESHOLDS['order_backlog']['critical'])})"
            ),
        })
    elif order_backlog > THRESHOLDS["order_backlog"]["warning"]:
        order_alerts.append({
            "type":     "BACKLOG_WARNING",
            "severity": "MEDIUM",
            "reason":   (
                f"Order backlog elevated: {order_backlog} orders queued "
                f"(threshold: {int(THRESHOLDS['order_backlog']['warning'])})"
            ),
        })

    # ── Step failure from real DB state ─────────────────────────────────────
    if order_status == "FAILED":
        order_alerts.append({
            "type":     "STEP_FAILURE",
            "severity": "HIGH",
            "reason":   (
                f"Step '{current_step}' failed: {failure_reason or 'Unknown error'}"
            ),
        })

    for a in order_alerts:
        if rank.get(a["severity"], 0) > rank.get(overall_severity, 0):
            overall_severity = a["severity"]

    return sla_status, overall_severity, order_alerts


async def fetch_orders_node(state: dict) -> dict:
    """Generate randomized per-order metrics (~60% healthy / 25% warning / 15% critical).

    Order profile data (type, customer, step list) is read from the DB so the
    reports remain meaningful.  SLA timing and fulfillment KPIs are generated
    probabilistically so the health distribution is realistic on every run.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    async with AsyncSessionLocal() as db:
        orders    = (await db.execute(
            select(ServiceOrder).where(ServiceOrder.status != "COMPLETED")
        )).scalars().all()
        step_rows = (await db.execute(select(ProvisioningStep))).scalars().all()

    steps_by_order: dict[int, list] = {}
    for s in step_rows:
        steps_by_order.setdefault(s.order_id, []).append(s)

    order_reports: list[dict] = []
    alerts:        list[dict] = []

    for order in orders:
        sla_h = SLA_HOURS.get(order.order_type, 24)

        # ── Probabilistic metric generation ─────────────────────────────────
        m             = _random_metrics(sla_h)
        elapsed_pct   = m["elapsed_pct"]
        elapsed_hours = m["elapsed_hours"]
        prov_success  = m["provisioning_success_rate"]
        order_backlog = m["order_backlog"]
        sla_breach_rt = m["sla_breach_rate"]

        sla_st, overall_severity, order_alerts = _severity(
            elapsed_pct   = elapsed_pct,
            prov_success  = prov_success,
            order_backlog = order_backlog,
            sla_breach_rate = sla_breach_rt,
            order_id      = order.id,
            sla_hours     = sla_h,
            order_status  = order.status,
            failure_reason = order.failure_reason,
            current_step  = order.current_step,
        )

        # ── Step summary from DB (actual provisioning state) ─────────────────
        order_steps  = sorted(steps_by_order.get(order.id, []), key=lambda s: s.id)
        step_summary = [
            {
                "step":     s.step_name,
                "status":   s.status,
                "duration": f"{s.duration_seconds}s" if s.duration_seconds is not None else None,
                "error":    s.error_message,
            }
            for s in order_steps
        ]

        report = {
            "order_id":      order.id,
            "order_type":    order.order_type,
            "customer_id":   order.customer_id,
            "customer_name": order.customer_name,
            "status":        order.status,
            "sla_status":    sla_st,
            "current_step":  order.current_step,
            "metrics": {
                "elapsed_hours":             f"{elapsed_hours}h",
                "sla_hours":                 f"{sla_h}h",
                "elapsed_pct":               f"{elapsed_pct}%",
                "provisioning_success_rate": f"{prov_success}%",
                "order_backlog":             str(order_backlog),
                "sla_breach_rate":           f"{sla_breach_rt}%",
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
    Only the top 4 highest-severity orders are sent to the LLM to keep response time sane."""
    alerts        = state.get("alerts", [])
    order_reports = state.get("order_reports", [])

    severity_rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0}
    alerts_sorted = sorted(
        alerts,
        key=lambda r: severity_rank.get(r["alert"]["severity"], 0),
        reverse=True,
    )
    llm_alerts  = alerts_sorted[:4]
    skipped_ids = {r["order_id"] for r in alerts_sorted[4:]}

    alert_blocks = []
    for r in llm_alerts:
        m       = r["metrics"]
        steps   = r["steps"]
        a_list  = r["alert"]["alerts"]
        step_log = "; ".join(
            f"{s['step']}={s['status']}"
            + (f"({s['duration']})" if s["duration"] else "")
            + (f"[ERR:{s['error']}]" if s["error"] else "")
            for s in steps
        )
        alert_log = " | ".join(a["reason"] for a in a_list)
        alert_blocks.append(
            f"Order    : {r['order_id']} ({r['order_type']}) — Customer: {r['customer_name']}\n"
            f"Status   : {r['status']} | SLA: {r['sla_status']} ({m['elapsed_pct']} of {m['sla_hours']})\n"
            f"Metrics  : Prov.Success={m['provisioning_success_rate']}, "
            f"Backlog={m['order_backlog']}, SLA Breach={m['sla_breach_rate']}\n"
            f"Steps    : {step_log}\n"
            f"Alerts   : {alert_log}"
        )

    system = SystemMessage(content=(
        "You are a Senior Telecom Service Fulfillment engineer.\n"
        "For each order alert, produce a structured RCA. "
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
        '    "recommendation": "Immediate next action",\n'
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
                report["alert"]["recommendation"] = (
                    "Queued for analysis — lower priority than current critical alerts"
                )
            else:
                ana = analy_map.get(report["order_id"], {})
                report["alert"]["rca"]            = ana.get("rca", {})
                report["alert"]["recommendation"] = ana.get("recommendation", "Manual investigation required")
                report["alert"]["reasoning"]      = ana.get("reasoning", "")
                report["alert"]["is_ambiguous"]   = ana.get("is_ambiguous", False)

    breached = sum(1 for r in order_reports if r["sla_status"] == "BREACHED")
    at_risk  = sum(1 for r in order_reports if r["sla_status"] == "AT_RISK")
    on_track = sum(1 for r in order_reports if r["sla_status"] == "ON_TRACK")
    failed   = sum(1 for r in order_reports if r["status"] == "FAILED")

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
