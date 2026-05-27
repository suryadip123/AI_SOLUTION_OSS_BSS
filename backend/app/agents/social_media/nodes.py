import json
import re
import random
from datetime import datetime, timezone
from sqlalchemy import select
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base_agent import get_llm
from app.db.database import AsyncSessionLocal
from app.db.models.social_media import SocialChannel
from app.agents.social_media.tools import THRESHOLDS

llm = get_llm()


def _random_metrics() -> dict:
    """Generate social-media sentiment metrics with ~60% healthy / 25% warning / 15% critical split.

    Tier boundaries derived from THRESHOLDS:
      nps_score          : warn<30,   crit<0    (below = worse)
      negative_sentiment : warn>20%,  crit>40%  (above = worse)
      complaint_volume   : warn>50/d, crit>100/d (above = worse)
    """
    tier = random.choices(
        population=["healthy", "warning", "critical"],
        weights=[0.60, 0.25, 0.15],
        k=1,
    )[0]

    if tier == "healthy":
        nps        = round(random.uniform(30.0,  100.0), 1)
        neg        = round(random.uniform(0.0,    19.9), 2)
        complaints = round(random.uniform(0.0,    49.9), 1)
    elif tier == "warning":
        nps        = round(random.uniform(0.0,    29.9), 1)
        neg        = round(random.uniform(20.0,   39.9), 2)
        complaints = round(random.uniform(50.0,   99.9), 1)
    else:  # critical
        nps        = round(random.uniform(-100.0,  -0.1), 1)
        neg        = round(random.uniform(40.0,    80.0), 2)
        complaints = round(random.uniform(100.0,  300.0), 1)

    return {
        "nps_score":          nps,
        "negative_sentiment": neg,
        "complaint_volume":   complaints,
    }


def _severity(nps: float, neg: float, complaints: float):
    """Return (status, severity, breaches) for a social media channel."""
    status   = "HEALTHY"
    severity = "NONE"
    breaches = []

    checks = [
        ("NPS Score",         nps,        "nps_score"),
        ("Negative Sentiment", neg,        "negative_sentiment"),
        ("Complaint Volume",   complaints, "complaint_volume"),
    ]
    for label, val, key in checks:
        cfg   = THRESHOLDS[key]
        below = cfg["direction"] == "below"
        unit  = "/day" if key == "complaint_volume" else ("%" if key == "negative_sentiment" else "")
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
                status   = "NEGATIVE"
                severity = "WARNING"

    return status, severity, breaches


async def fetch_metrics_node(state: dict) -> dict:
    """Generate randomized metrics (~60% healthy / 25% warning / 15% critical) per channel.

    Channel profile data (platform, total_mentions) is read from the DB for context;
    live sentiment KPIs are generated probabilistically on every run.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(SocialChannel))).scalars().all()

    reports: list[dict] = []
    alerts:  list[dict] = []

    for ch in rows:
        # ── Probabilistic metric generation ─────────────────────────────────
        m          = _random_metrics()
        nps        = m["nps_score"]
        neg        = m["negative_sentiment"]
        complaints = m["complaint_volume"]

        status, severity, breaches = _severity(nps, neg, complaints)

        report = {
            "channel_id":      ch.channel_id,
            "platform":        ch.platform,
            "total_mentions":  ch.total_mentions,
            "status":          status,
            "metrics": {
                "nps_score":          str(nps),
                "negative_sentiment": f"{neg}%",
                "complaint_volume":   f"{complaints}/day",
            },
            "alert": {
                "raised":         bool(breaches),
                "severity":       severity,
                "reason":         "; ".join(breaches) if breaches else "Sentiment metrics normal",
                "timestamp":      timestamp,
                "root_cause":     "",
                "recommendation": "",
                "reasoning":      "",
            },
        }
        reports.append(report)
        if breaches:
            alerts.append(report)

    return {"channel_reports": reports, "alerts": alerts}


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
    """Call LLM for root-cause analysis on negative / critical social media channels."""
    alerts  = state.get("alerts", [])
    reports = state.get("channel_reports", [])

    rank    = {"CRITICAL": 4, "WARNING": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0}
    top     = sorted(alerts, key=lambda r: rank.get(r["alert"]["severity"], 0), reverse=True)[:3]
    skipped = {r["channel_id"] for r in alerts if r not in top}

    blocks = [
        f"Channel : {r['platform']} ({r['channel_id']}, Mentions: {r['total_mentions']})\n"
        f"Status  : {r['status']}\n"
        f"Metrics : NPS={r['metrics']['nps_score']}, "
        f"Negative={r['metrics']['negative_sentiment']}, "
        f"Complaints={r['metrics']['complaint_volume']}\n"
        f"Breach  : {r['alert']['reason']}"
        for r in top
    ]

    system = SystemMessage(content=(
        "You are a Senior Telecom Brand & Customer Experience analyst.\n"
        "For each negative or critical social media channel provide:\n"
        "  root_cause     — what is driving the negative sentiment (2-3 sentences)\n"
        "  recommendation — specific PR and operational actions to take (2-3 sentences)\n"
        "  reasoning      — why you concluded this root cause (1-2 sentences)\n\n"
        "Output ONLY a raw JSON array, one object per channel:\n"
        '[{"channel_id":"...","root_cause":"...","recommendation":"...","reasoning":"..."}]'
    ))
    human = HumanMessage(
        content="Analyze these social media sentiment alerts:\n\n" + "\n\n".join(blocks)
    )

    response = await llm.ainvoke([system, human])
    analyses = _parse_llm_json(response.content)
    amap     = {a["channel_id"]: a for a in analyses if isinstance(a, dict)}

    for r in reports:
        if r["alert"]["raised"]:
            if r["channel_id"] in skipped:
                r["alert"]["recommendation"] = (
                    "Queued — lower priority than current critical channels"
                )
            else:
                ana = amap.get(r["channel_id"], {})
                r["alert"]["root_cause"]     = ana.get("root_cause",     "Analysis unavailable")
                r["alert"]["recommendation"] = ana.get("recommendation", "Manual investigation required")
                r["alert"]["reasoning"]      = ana.get("reasoning",      "")

    critical = sum(1 for r in reports if r["status"] == "CRITICAL")
    negative = sum(1 for r in reports if r["status"] == "NEGATIVE")
    healthy  = sum(1 for r in reports if r["status"] == "HEALTHY")

    result = {
        "summary": {
            "total_channels": len(reports),
            "critical":       critical,
            "negative":       negative,
            "healthy":        healthy,
            "alerts_raised":  len(alerts),
        },
        "channel_reports": reports,
    }
    return {"result": result, "status": "completed", "messages": [response]}


def should_analyze(state: dict) -> str:
    return "analyze" if state.get("alerts") else "end"
