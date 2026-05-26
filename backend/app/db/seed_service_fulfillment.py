from datetime import datetime, timedelta
from sqlalchemy import select, func
from app.db.database import AsyncSessionLocal
from app.db.models.service_fulfillment import ServiceOrder, ProvisioningStep, StepMetrics

STEPS = ["Validate", "Allocate Resource", "Configure", "Activate", "Confirm"]

SLA_HOURS = {
    "SIM_ACTIVATION":  2,
    "BROADBAND":       24,
    "NUMBER_PORTING":  72,
}

# Baseline average durations per step (seconds)
_STEP_METRICS = [
    {"step_name": "Validate",          "avg_duration_seconds": 30.0},
    {"step_name": "Allocate Resource", "avg_duration_seconds": 120.0},
    {"step_name": "Configure",         "avg_duration_seconds": 180.0},
    {"step_name": "Activate",          "avg_duration_seconds": 240.0},
    {"step_name": "Confirm",           "avg_duration_seconds": 60.0},
]

# (order_id, type, customer_id, customer_name, age_hours, status, current_step, failure_reason)
_ORDERS = [
    # SIM Activation (SLA = 2h) — at_risk at 1.6h
    ("ORD-001", "SIM_ACTIVATION", "CUST-101", "Alice Johnson",  1.7,  "PROVISIONING", "Configure",        None),
    ("ORD-002", "SIM_ACTIVATION", "CUST-102", "Bob Smith",      0.3,  "VALIDATING",   "Validate",         None),
    ("ORD-003", "SIM_ACTIVATION", "CUST-103", "Carol White",    2.5,  "FAILED",       "Activate",         "SIM card allocation timeout after 3 retries"),
    # Broadband Provisioning (SLA = 24h) — at_risk at 19.2h
    ("ORD-004", "BROADBAND",      "CUST-201", "David Lee",      26.0, "TESTING",      "Confirm",          None),
    ("ORD-005", "BROADBAND",      "CUST-202", "Emma Davis",     20.0, "PROVISIONING", "Activate",         None),
    ("ORD-006", "BROADBAND",      "CUST-203", "Frank Moore",    4.0,  "PROVISIONING", "Configure",        None),
    ("ORD-007", "BROADBAND",      "CUST-204", "Grace Kim",      28.0, "FAILED",       "Configure",        "CPE configuration mismatch — VLAN ID conflict on port 4"),
    # Number Porting (SLA = 72h) — at_risk at 57.6h
    ("ORD-008", "NUMBER_PORTING", "CUST-301", "Henry Park",     60.0, "PROVISIONING", "Activate",         None),
    ("ORD-009", "NUMBER_PORTING", "CUST-302", "Iris Chen",      10.0, "VALIDATING",   "Allocate Resource",None),
    ("ORD-010", "NUMBER_PORTING", "CUST-303", "Jack Taylor",    75.0, "TESTING",      "Confirm",          None),
]


def _make_steps(order_id: str, current_step: str, order_status: str, order_age_hours: float):
    """Build ProvisioningStep rows for a given order."""
    rows = []
    now  = datetime.utcnow()
    t    = now - timedelta(hours=order_age_hours)   # order created_at

    current_idx = STEPS.index(current_step) if current_step in STEPS else 0

    for i, step in enumerate(STEPS):
        if i < current_idx:
            # Completed steps — realistic durations with some variance
            base_dur = [30, 120, 180, 240, 60][i]
            variance = base_dur * 0.2
            import random
            rng = random.Random(hash(order_id + step))
            dur  = base_dur + rng.uniform(-variance, variance)
            start = t
            end   = t + timedelta(seconds=dur)
            rows.append(ProvisioningStep(
                order_id=order_id, step_name=step, status="COMPLETED",
                start_time=start, end_time=end, duration_seconds=round(dur, 1),
            ))
            t = end
        elif i == current_idx:
            if order_status == "FAILED":
                # Failed step — has start and end, error message set at order level
                base_dur = [30, 120, 180, 240, 60][i] * 2.5   # took much longer
                start = t
                end   = t + timedelta(seconds=base_dur)
                rows.append(ProvisioningStep(
                    order_id=order_id, step_name=step, status="FAILED",
                    start_time=start, end_time=end, duration_seconds=round(base_dur, 1),
                    error_message="Step failed — see order failure_reason",
                ))
            else:
                # Currently running — start_time set, no end_time yet
                rows.append(ProvisioningStep(
                    order_id=order_id, step_name=step, status="RUNNING",
                    start_time=t, end_time=None, duration_seconds=None,
                ))
        else:
            # Future steps — pending
            rows.append(ProvisioningStep(
                order_id=order_id, step_name=step, status="PENDING",
                start_time=None, end_time=None, duration_seconds=None,
            ))
    return rows


async def seed_service_fulfillment_data():
    async with AsyncSessionLocal() as db:
        count = (await db.execute(select(func.count()).select_from(ServiceOrder))).scalar()
        if count and count > 0:
            return

        now = datetime.utcnow()

        # Seed step metrics baseline
        for sm in _STEP_METRICS:
            db.add(StepMetrics(**sm))

        # Seed orders + steps
        for (oid, otype, cid, cname, age_h, status, curr_step, failure) in _ORDERS:
            created = now - timedelta(hours=age_h)
            sla_h   = SLA_HOURS[otype]
            elapsed_pct = (age_h / sla_h) * 100
            if elapsed_pct >= 100:
                sla_status = "BREACHED"
            elif elapsed_pct >= 80:
                sla_status = "AT_RISK"
            else:
                sla_status = "ON_TRACK"

            order = ServiceOrder(
                id=oid, order_type=otype, customer_id=cid, customer_name=cname,
                status=status, current_step=curr_step, failure_reason=failure,
                sla_status=sla_status, created_at=created,
            )
            db.add(order)

            for step_row in _make_steps(oid, curr_step, status, age_h):
                db.add(step_row)

        await db.commit()
