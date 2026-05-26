from sqlalchemy import select, func
from app.db.database import AsyncSessionLocal
from app.db.models.call import CallGateway

_GATEWAYS = [
    dict(gateway_id="GW-NORTH-01", region="North", call_success_rate=98.0, call_drop_rate=1.0, avg_duration_min=4.5, total_calls=12500),
    dict(gateway_id="GW-NORTH-02", region="North", call_success_rate=89.0, call_drop_rate=8.2, avg_duration_min=1.8, total_calls=9800),
    dict(gateway_id="GW-SOUTH-01", region="South", call_success_rate=97.0, call_drop_rate=2.1, avg_duration_min=3.8, total_calls=11200),
    dict(gateway_id="GW-SOUTH-02", region="South", call_success_rate=93.0, call_drop_rate=4.5, avg_duration_min=2.5, total_calls=8700),
    dict(gateway_id="GW-EAST-01",  region="East",  call_success_rate=99.0, call_drop_rate=0.5, avg_duration_min=5.2, total_calls=14300),
    dict(gateway_id="GW-EAST-02",  region="East",  call_success_rate=91.0, call_drop_rate=6.3, avg_duration_min=1.5, total_calls=7600),
    dict(gateway_id="GW-WEST-01",  region="West",  call_success_rate=96.0, call_drop_rate=2.8, avg_duration_min=3.1, total_calls=10100),
    dict(gateway_id="GW-WEST-02",  region="West",  call_success_rate=88.0, call_drop_rate=9.1, avg_duration_min=0.8, total_calls=6200),
    dict(gateway_id="GW-CORE-01",  region="Core",  call_success_rate=99.5, call_drop_rate=0.3, avg_duration_min=4.8, total_calls=18900),
    dict(gateway_id="GW-CORE-02",  region="Core",  call_success_rate=94.0, call_drop_rate=3.5, avg_duration_min=2.2, total_calls=16400),
]

async def seed_call_data():
    async with AsyncSessionLocal() as db:
        count = (await db.execute(select(func.count()).select_from(CallGateway))).scalar()
        if count and count > 0:
            return
        for gw in _GATEWAYS:
            db.add(CallGateway(**gw))
        await db.commit()
