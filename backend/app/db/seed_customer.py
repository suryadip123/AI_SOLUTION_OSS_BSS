from sqlalchemy import select, func
from app.db.database import AsyncSessionLocal
from app.db.models.customer import CustomerAccount

_ACCOUNTS = [
    # Enterprise
    dict(account_id="ENT-001", name="Apex Telecom Ltd",       segment="Enterprise",  region="North", plan="Premium",  active_orders=12, order_completion_rate=95.0, avg_fulfillment_time=24.0, sla_breach_rate=1.0),
    dict(account_id="ENT-002", name="Horizon Networks",        segment="Enterprise",  region="South", plan="Premium",  active_orders=28, order_completion_rate=65.0, avg_fulfillment_time=80.0, sla_breach_rate=22.0),
    dict(account_id="ENT-003", name="BlueStar Communications", segment="Enterprise",  region="East",  plan="Standard", active_orders=19, order_completion_rate=82.0, avg_fulfillment_time=55.0, sla_breach_rate=7.0),
    # SMB
    dict(account_id="SMB-001", name="QuickConnect Ltd",        segment="SMB",         region="North", plan="Standard", active_orders=5,  order_completion_rate=93.0, avg_fulfillment_time=36.0, sla_breach_rate=2.0),
    dict(account_id="SMB-002", name="DataBridge Solutions",    segment="SMB",         region="West",  plan="Standard", active_orders=14, order_completion_rate=68.0, avg_fulfillment_time=68.0, sla_breach_rate=18.0),
    dict(account_id="SMB-003", name="NexGen Retail Tech",      segment="SMB",         region="South", plan="Basic",    active_orders=7,  order_completion_rate=87.0, avg_fulfillment_time=42.0, sla_breach_rate=4.0),
    # Retail
    dict(account_id="RTL-001", name="ShopLink Networks",       segment="Retail",      region="East",  plan="Basic",    active_orders=21, order_completion_rate=72.0, avg_fulfillment_time=75.0, sla_breach_rate=19.0),
    dict(account_id="RTL-002", name="MarketEdge Telecom",      segment="Retail",      region="North", plan="Standard", active_orders=9,  order_completion_rate=91.0, avg_fulfillment_time=28.0, sla_breach_rate=3.0),
    # Government
    dict(account_id="GOV-001", name="City Infrastructure Dept",segment="Government",  region="West",  plan="Premium",  active_orders=11, order_completion_rate=80.0, avg_fulfillment_time=52.0, sla_breach_rate=8.0),
    dict(account_id="GOV-002", name="State Broadband Authority",segment="Government", region="South", plan="Premium",  active_orders=16, order_completion_rate=77.0, avg_fulfillment_time=60.0, sla_breach_rate=11.0),
]


async def seed_customer_data():
    async with AsyncSessionLocal() as db:
        count = (await db.execute(select(func.count()).select_from(CustomerAccount))).scalar()
        if count and count > 0:
            return
        for acc in _ACCOUNTS:
            db.add(CustomerAccount(**acc))
        await db.commit()
