import json, re, random
from datetime import datetime, timezone
from sqlalchemy import select
from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.base_agent import get_llm
from app.db.database import AsyncSessionLocal
from app.db.models.call import CallGateway
from app.agents.call.tools import THRESHOLDS

llm = get_llm()

def _jitter(v, pct=0.10, lo=0.0, hi=100.0):
    return round(max(lo, min(hi, v + v * pct * (random.random() * 2 - 1))), 2)

def _evaluate(success, drop, duration):
    status, severity, breaches = "HEALTHY", "NONE", []
    for label, val, key in [("Call Success Rate", success, "call_success_rate"), ("Call Drop Rate", drop, "call_drop_rate"), ("Avg Duration", duration, "avg_duration_min")]:
        cfg = THRESHOLDS[key]; below = cfg["direction"] == "below"
        unit = "%" if key != "avg_duration_min" else "min"
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
        rows = (await db.execute(select(CallGateway))).scalars().all()
    reports, alerts = [], []
    for gw in rows:
        success  = _jitter(gw.call_success_rate, pct=0.05, lo=70.0,  hi=100.0)
        drop     = _jitter(gw.call_drop_rate,    pct=0.20, lo=0.0,   hi=25.0)
        duration = _jitter(gw.avg_duration_min,  pct=0.15, lo=0.1,   hi=15.0)
        status, severity, breaches = _evaluate(success, drop, duration)
        report = {
            "gateway_id": gw.gateway_id, "region": gw.region, "total_calls": gw.total_calls,
            "status": status,
            "metrics": {"success_rate": f"{success}%", "drop_rate": f"{drop}%", "avg_duration": f"{duration}min"},
            "alert": {"raised": bool(breaches), "severity": severity,
                      "reason": "; ".join(breaches) if breaches else "All call metrics normal",
                      "timestamp": ts, "root_cause": "", "recommendation": "", "reasoning": ""},
        }
        reports.append(report)
        if breaches: alerts.append(report)
    return {"call_reports": reports, "alerts": alerts}

async def analyze_alerts_node(state):
    alerts, reports = state.get("alerts", []), state.get("call_reports", [])
    rank = {"CRITICAL":4,"WARNING":3,"MEDIUM":2,"LOW":1,"NONE":0}
    top = sorted(alerts, key=lambda r: rank.get(r["alert"]["severity"],0), reverse=True)[:3]
    skipped = {r["gateway_id"] for r in alerts if r not in top}
    blocks = [f"Gateway: {r['gateway_id']} (Region: {r['region']}, Calls: {r['total_calls']})\nStatus: {r['status']}\n"
              f"Metrics: Success={r['metrics']['success_rate']}, Drop={r['metrics']['drop_rate']}, Duration={r['metrics']['avg_duration']}\n"
              f"Breach: {r['alert']['reason']}" for r in top]
    system = SystemMessage(content=(
        "You are a Senior Telecom Call Operations engineer. For each degraded/critical gateway provide "
        "root_cause (2-3 sentences), recommendation (2-3 sentences), reasoning (1-2 sentences).\n"
        'Output ONLY a raw JSON array: [{"gateway_id":"...","root_cause":"...","recommendation":"...","reasoning":"..."}]'
    ))
    response = await llm.ainvoke([system, HumanMessage(content="Analyze:\n\n" + "\n\n".join(blocks))])
    amap = {a["gateway_id"]: a for a in _parse_json(response.content) if isinstance(a, dict)}
    for r in reports:
        if r["alert"]["raised"]:
            if r["gateway_id"] in skipped:
                r["alert"]["recommendation"] = "Queued — lower priority than current critical alerts"
            else:
                ana = amap.get(r["gateway_id"], {})
                r["alert"]["root_cause"]     = ana.get("root_cause", "Analysis unavailable")
                r["alert"]["recommendation"] = ana.get("recommendation", "Manual investigation required")
                r["alert"]["reasoning"]      = ana.get("reasoning", "")
    crit = sum(1 for r in reports if r["status"] == "CRITICAL")
    deg  = sum(1 for r in reports if r["status"] == "DEGRADED")
    heal = sum(1 for r in reports if r["status"] == "HEALTHY")
    return {"result": {"summary": {"total_gateways": len(reports), "critical": crit, "degraded": deg, "healthy": heal, "alerts_raised": len(alerts)}, "call_reports": reports}, "status": "completed", "messages": [response]}

def should_analyze(state): return "analyze" if state.get("alerts") else "end"
