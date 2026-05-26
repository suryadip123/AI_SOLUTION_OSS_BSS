from sqlalchemy import select, func
from app.db.database import AsyncSessionLocal
from app.db.models.billing import BillingAccount

_ACCOUNTS = [
    dict(account_id="BILL-ENT-001", name="Apex Telecom Ltd",        segment="Enterprise", region="North", bill_gen_success_rate=98.0, payment_collection_rate=96.0, dispute_rate=1.0,  total_bills=240),
    dict(account_id="BILL-ENT-002", name="Horizon Networks",         segment="Enterprise", region="South", bill_gen_success_rate=82.0, payment_collection_rate=71.0, dispute_rate=9.5,  total_bills=185),
    dict(account_id="BILL-ENT-003", name="BlueStar Communications",  segment="Enterprise", region="East",  bill_gen_success_rate=94.0, payment_collection_rate=88.0, dispute_rate=4.2,  total_bills=210),
    dict(account_id="BILL-SMB-001", name="QuickConnect Ltd",         segment="SMB",        region="North", bill_gen_success_rate=97.0, payment_collection_rate=94.0, dispute_rate=2.0,  total_bills=95),
    dict(account_id="BILL-SMB-002", name="DataBridge Solutions",     segment="SMB",        region="West",  bill_gen_success_rate=80.0, payment_collection_rate=68.0, dispute_rate=11.0, total_bills=112),
    dict(account_id="BILL-SMB-003", name="NexGen Retail Tech",       segment="SMB",        region="South", bill_gen_success_rate=96.0, payment_collection_rate=91.0, dispute_rate=2.5,  total_bills=78),
    dict(account_id="BILL-RTL-001", name="ShopLink Networks",        segment="Retail",     region="East",  bill_gen_success_rate=86.0, payment_collection_rate=77.0, dispute_rate=6.0,  total_bills=320),
    dict(account_id="BILL-RTL-002", name="MarketEdge Telecom",       segment="Retail",     region="North", bill_gen_success_rate=99.0, payment_collection_rate=97.0, dispute_rate=1.0,  total_bills=280),
    dict(account_id="BILL-GOV-001", name="City Infrastructure Dept", segment="Government", region="West",  bill_gen_success_rate=93.0, payment_collection_rate=85.0, dispute_rate=4.0,  total_bills=60),
    dict(account_id="BILL-GOV-002", name="State Broadband Authority",segment="Government", region="South", bill_gen_success_rate=78.0, payment_collection_rate=65.0, dispute_rate=12.0, total_bills=48),
]

async def seed_billing_data():
    async with AsyncSessionLocal() as db:
        count = (await db.execute(select(func.count()).select_from(BillingAccount))).scalar()
        if count and count > 0:
            return
        for acc in _ACCOUNTS:
            db.add(BillingAccount(**acc))
        await db.commit()
