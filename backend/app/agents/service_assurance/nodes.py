import json, re, random
from datetime import datetime, timezone
from sqlalchemy import select
from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.base_agent import get_llm
from app.db.database import AsyncSessionLocal
from app.db.models.service_assurance import ServiceEndpoint
from app.agents.service_assurance.tools import THRESHOLDS

llm = get_llm()

def _jitter(v, pct=0.15, lo=0.0, hi=100.0):
    return round(max(lo, min(hi, v + v * pct * (random.random() * 2 - 1))), 2)

def _evaluate(avail, error, mttr):
    status, severity, breaches = "HEALTHY", "NONE", []
    for label, val, key in [("Availability", avail, "availability_pct"), ("Error Rate", error, "error_rate_pct"), ("MTTR", mttr, "mttr_hours")]:
        cfg = THRESHOLDS[key]; below = cfg["direction"] == "below"
        unit = "%" if key != "mttr_hours" else "h"
        if (below and val < cfg["critical"]) or (not below and val > cfg["critical"]):
            breaches.append(f"{label} at {val}{unit} breaches CRITICAL ({cfg['critical']}{unit})")
            status, severity = "CRITICAL", "CRITICAL"
        elif (below and val < cfg["warning"]) or (not below and val > cfg["warning"]):
            breaches.append(f"{label} at {val}{unit} breaches WARNING ({cfg['warning']}{unit})")
            if status != "CRITICAL": status, severity = "DEGRADED", "WARNING"
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
        rows = (await db.execute(select(ServiceEndpoint))).scalars().all()
    reports, alerts = [], []
    for svc in rows:
        avail = _jitter(svc.availability_pct, pct=0.005, lo=90.0, hi=100.0)
        error = _jitter(svc.error_rate_pct,   pct=0.20,  lo=0.0,  hi=30.0)
        mttr  = _jitter(svc.mttr_hours,       pct=0.20,  lo=0.0,  hi=48.0)
        status, severity, breaches = _evaluate(avail, error, mttr)
        report = {
            "service_id": svc.service_id, "name": svc.name, "service_type": svc.service_type, "region": svc.region,
            "status": status,
            "metrics": {"availability": f"{avail}%", "error_rate": f"{error}%", "mttr": f"{mttr}h"},
            "alert": {"raised": bool(breaches), "severity": severity,
                      "reason": "; ".join(breaches) if breaches else "All metrics normal",
                      "timestamp": ts, "root_cause": "", "recommendation": "", "reasoning": ""},
        }
        reports.append(report)
        if breaches: alerts.append(report)
    return {"service_reports": reports, "alerts": alerts}

async def analyze_alerts_node(state):
    alerts, reports = state.get("alerts", []), state.get("service_reports", [])
    rank = {"CRITICAL":4,"WARNING":3,"MEDIUM":2,"LOW":1,"NONE":0}
    top = sorted(alerts, key=lambda r: rank.get(r["alert"]["severity"],0), reverse=True)[:3]
    skipped = {r["service_id"] for r in alerts if r not in top}
    blocks = [f"Service: {r['name']} ({r['service_type']}, {r['region']})\nStatus: {r['status']}\n"
              f"Metrics: Avail={r['metrics']['availability']}, Err={r['metrics']['error_rate']}, MTTR={r['metrics']['mttr']}\n"
              f"Breach: {r['alert']['reason']}" for r in top]
    system = SystemMessage(content=(
        "You are a Senior Telecom Service Assurance engineer. For each degraded/critical service provide "
        "root_cause (2-3 sentences), recommendation (2-3 sentences), reasoning (1-2 sentences).\n"
        'Output ONLY a raw JSON array: [{"service_id":"...","root_cause":"...","recommendation":"...","reasoning":"..."}]'
    ))
    response = await llm.ainvoke([system, HumanMessage(content="Analyze:\n\n" + "\n\n".join(blocks))])
    amap = {a["service_id"]: a for a in _parse_json(response.content) if isinstance(a, dict)}
    for r in reports:
        if r["alert"]["raised"]:
            if r["service_id"] in skipped:
                r["alert"]["recommendation"] = "Queued — lower priority than current critical alerts"
            else:
                ana = amap.get(r["service_id"], {})
                r["alert"]["root_cause"]     = ana.get("root_cause", "Analysis unavailable")
                r["alert"]["recommendation"] = ana.get("recommendation", "Manual investigation required")
                r["alert"]["reasoning"]      = ana.get("reasoning", "")
    crit = sum(1 for r in reports if r["status"] == "CRITICAL")
    deg  = sum(1 for r in reports if r["status"] == "DEGRADED")
    heal = sum(1 for r in reports if r["status"] == "HEALTHY")
    return {"result": {"summary": {"total_services": len(reports), "critical": crit, "degraded": deg, "healthy": heal, "alerts_raised": len(alerts)}, "service_reports": reports}, "status": "completed", "messages": [response]}

def should_analyze(state): return "analyze" if state.get("alerts") else "end"
