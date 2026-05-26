import json, re, random
from datetime import datetime, timezone
from sqlalchemy import select
from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.base_agent import get_llm
from app.db.database import AsyncSessionLocal
from app.db.models.social_media import SocialChannel
from app.agents.social_media.tools import THRESHOLDS

llm = get_llm()

def _jitter(v, pct=0.10, lo=-100.0, hi=100.0):
    return round(max(lo, min(hi, v + abs(v if v != 0 else 1) * pct * (random.random() * 2 - 1))), 2)

def _evaluate(nps, neg, complaints):
    status, severity, breaches = "HEALTHY", "NONE", []
    for label, val, key in [("NPS Score", nps, "nps_score"), ("Negative Sentiment", neg, "negative_sentiment"), ("Complaint Volume", complaints, "complaint_volume")]:
        cfg = THRESHOLDS[key]; below = cfg["direction"] == "below"
        unit = "/day" if key == "complaint_volume" else ("%" if key == "negative_sentiment" else "")
        if (below and val < cfg["critical"]) or (not below and val > cfg["critical"]):
            breaches.append(f"{label} at {val}{unit} breaches CRITICAL ({cfg['critical']}{unit})")
            status, severity = "CRITICAL", "CRITICAL"
        elif (below and val < cfg["warning"]) or (not below and val > cfg["warning"]):
            breaches.append(f"{label} at {val}{unit} breaches WARNING ({cfg['warning']}{unit})")
            if status != "CRITICAL": status, severity = "NEGATIVE", "WARNING"
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
        rows = (await db.execute(select(SocialChannel))).scalars().all()
    reports, alerts = [], []
    for ch in rows:
        nps        = _jitter(ch.nps_score,         pct=0.10, lo=-100.0, hi=100.0)
        neg        = _jitter(ch.negative_sentiment, pct=0.12, lo=0.0,   hi=100.0)
        complaints = _jitter(ch.complaint_volume,   pct=0.15, lo=0.0,   hi=500.0)
        status, severity, breaches = _evaluate(nps, neg, complaints)
        report = {
            "channel_id": ch.channel_id, "platform": ch.platform, "total_mentions": ch.total_mentions,
            "status": status,
            "metrics": {"nps_score": str(nps), "negative_sentiment": f"{neg}%", "complaint_volume": f"{complaints}/day"},
            "alert": {"raised": bool(breaches), "severity": severity,
                      "reason": "; ".join(breaches) if breaches else "Sentiment metrics normal",
                      "timestamp": ts, "root_cause": "", "recommendation": "", "reasoning": ""},
        }
        reports.append(report)
        if breaches: alerts.append(report)
    return {"channel_reports": reports, "alerts": alerts}

async def analyze_alerts_node(state):
    alerts, reports = state.get("alerts", []), state.get("channel_reports", [])
    rank = {"CRITICAL":4,"WARNING":3,"MEDIUM":2,"LOW":1,"NONE":0}
    top = sorted(alerts, key=lambda r: rank.get(r["alert"]["severity"],0), reverse=True)[:3]
    skipped = {r["channel_id"] for r in alerts if r not in top}
    blocks = [f"Channel: {r['platform']} ({r['channel_id']})\nStatus: {r['status']}\n"
              f"Metrics: NPS={r['metrics']['nps_score']}, Negative={r['metrics']['negative_sentiment']}, Complaints={r['metrics']['complaint_volume']}\n"
              f"Breach: {r['alert']['reason']}" for r in top]
    system = SystemMessage(content=(
        "You are a Senior Telecom Brand & Customer Experience analyst. For each negative/critical social media channel provide "
        "root_cause (2-3 sentences about what's driving negative sentiment), recommendation (2-3 sentences of PR/ops actions), reasoning (1-2 sentences).\n"
        'Output ONLY a raw JSON array: [{"channel_id":"...","root_cause":"...","recommendation":"...","reasoning":"..."}]'
    ))
    response = await llm.ainvoke([system, HumanMessage(content="Analyze:\n\n" + "\n\n".join(blocks))])
    amap = {a["channel_id"]: a for a in _parse_json(response.content) if isinstance(a, dict)}
    for r in reports:
        if r["alert"]["raised"]:
            if r["channel_id"] in skipped:
                r["alert"]["recommendation"] = "Queued — lower priority than current critical channels"
            else:
                ana = amap.get(r["channel_id"], {})
                r["alert"]["root_cause"]     = ana.get("root_cause", "Analysis unavailable")
                r["alert"]["recommendation"] = ana.get("recommendation", "Manual investigation required")
                r["alert"]["reasoning"]      = ana.get("reasoning", "")
    crit = sum(1 for r in reports if r["status"] == "CRITICAL")
    neg  = sum(1 for r in reports if r["status"] == "NEGATIVE")
    heal = sum(1 for r in reports if r["status"] == "HEALTHY")
    return {"result": {"summary": {"total_channels": len(reports), "critical": crit, "negative": neg, "healthy": heal, "alerts_raised": len(alerts)}, "channel_reports": reports}, "status": "completed", "messages": [response]}

def should_analyze(state): return "analyze" if state.get("alerts") else "end"
