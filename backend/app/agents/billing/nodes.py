import json, re, random
from datetime import datetime, timezone
from sqlalchemy import select
from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.base_agent import get_llm
from app.db.database import AsyncSessionLocal
from app.db.models.billing import BillingAccount
from app.agents.billing.tools import THRESHOLDS

llm = get_llm()

def _jitter(v, pct=0.08, lo=0.0, hi=100.0):
    return round(max(lo, min(hi, v + v * pct * (random.random() * 2 - 1))), 2)

def _evaluate(gen, pay, dispute):
    status, severity, breaches = "HEALTHY", "NONE", []
    for label, val, key in [("Bill Gen Rate", gen, "bill_gen_success_rate"), ("Payment Rate", pay, "payment_collection_rate"), ("Dispute Rate", dispute, "dispute_rate")]:
        cfg = THRESHOLDS[key]; below = cfg["direction"] == "below"
        if (below and val < cfg["critical"]) or (not below and val > cfg["critical"]):
            breaches.append(f"{label} at {val}% breaches CRITICAL ({cfg['critical']}%)")
            status, severity = "CRITICAL", "CRITICAL"
        elif (below and val < cfg["warning"]) or (not below and val > cfg["warning"]):
            breaches.append(f"{label} at {val}% breaches WARNING ({cfg['warning']}%)")
            if status != "CRITICAL": status, severity = "AT_RISK", "WARNING"
    return status, severity, breaches

def _parse_json(text):
    for s in [text.strip(), re.sub(r"```(?:json)?","",text).strip().rstrip("`")]:
        try: return json.loads(s)
        except: pass
    m = re.search(r"\[.*?\]", text, re.DOTALL)
    if m:
        try: return json.loads(m.group())
        except: pass
    return []

async def fetch_metrics_node(state):
    ts = datetime.now(timezone.utc).isoformat()
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(BillingAccount))).scalars().all()
    reports, alerts = [], []
    for acc in rows:
        gen     = _jitter(acc.bill_gen_success_rate,   pct=0.05, lo=50.0, hi=100.0)
        pay     = _jitter(acc.payment_collection_rate, pct=0.08, lo=40.0, hi=100.0)
        dispute = _jitter(acc.dispute_rate,            pct=0.15, lo=0.0,  hi=30.0)
        status, severity, breaches = _evaluate(gen, pay, dispute)
        report = {
            "account_id": acc.account_id, "name": acc.name, "segment": acc.segment, "region": acc.region,
            "total_bills": acc.total_bills, "status": status,
            "metrics": {"bill_gen_rate": f"{gen}%", "payment_rate": f"{pay}%", "dispute_rate": f"{dispute}%"},
            "alert": {"raised": bool(breaches), "severity": severity,
                      "reason": "; ".join(breaches) if breaches else "All billing metrics normal",
                      "timestamp": ts, "root_cause": "", "recommendation": "", "reasoning": ""},
        }
        reports.append(report)
        if breaches: alerts.append(report)
    return {"billing_reports": reports, "alerts": alerts}

async def analyze_alerts_node(state):
    alerts, reports = state.get("alerts", []), state.get("billing_reports", [])
    rank = {"CRITICAL":4,"WARNING":3,"MEDIUM":2,"LOW":1,"NONE":0}
    top = sorted(alerts, key=lambda r: rank.get(r["alert"]["severity"],0), reverse=True)[:3]
    skipped = {r["account_id"] for r in alerts if r not in top}
    blocks = [f"Account: {r['account_id']} — {r['name']} ({r['segment']})\nStatus: {r['status']}\n"
              f"Metrics: Gen={r['metrics']['bill_gen_rate']}, Pay={r['metrics']['payment_rate']}, Dispute={r['metrics']['dispute_rate']}\n"
              f"Breach: {r['alert']['reason']}" for r in top]
    system = SystemMessage(content=(
        "You are a Senior Telecom Billing Operations analyst. For each at-risk/critical billing account provide "
        "root_cause (2-3 sentences), recommendation (2-3 sentences), reasoning (1-2 sentences).\n"
        'Output ONLY a raw JSON array: [{"account_id":"...","root_cause":"...","recommendation":"...","reasoning":"..."}]'
    ))
    response = await llm.ainvoke([system, HumanMessage(content="Analyze:\n\n" + "\n\n".join(blocks))])
    amap = {a["account_id"]: a for a in _parse_json(response.content) if isinstance(a, dict)}
    for r in reports:
        if r["alert"]["raised"]:
            if r["account_id"] in skipped:
                r["alert"]["recommendation"] = "Queued — lower priority than current critical alerts"
            else:
                ana = amap.get(r["account_id"], {})
                r["alert"]["root_cause"]     = ana.get("root_cause", "Analysis unavailable")
                r["alert"]["recommendation"] = ana.get("recommendation", "Manual investigation required")
                r["alert"]["reasoning"]      = ana.get("reasoning", "")
    crit = sum(1 for r in reports if r["status"] == "CRITICAL")
    risk = sum(1 for r in reports if r["status"] == "AT_RISK")
    heal = sum(1 for r in reports if r["status"] == "HEALTHY")
    return {"result": {"summary": {"total_accounts": len(reports), "critical": crit, "at_risk": risk, "healthy": heal, "alerts_raised": len(alerts)}, "billing_reports": reports}, "status": "completed", "messages": [response]}

def should_analyze(state): return "analyze" if state.get("alerts") else "end"
