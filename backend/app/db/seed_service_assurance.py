from sqlalchemy import select, func
from app.db.database import AsyncSessionLocal
from app.db.models.service_assurance import ServiceEndpoint

_SERVICES = [
    dict(service_id="SVC-VOIP-CORE",  name="VoIP Core",            service_type="VoIP",     region="Core",  availability_pct=99.9, error_rate_pct=0.1, mttr_hours=1.0),
    dict(service_id="SVC-VOIP-EDGE",  name="VoIP Edge",            service_type="VoIP",     region="Edge",  availability_pct=98.8, error_rate_pct=4.2, mttr_hours=5.2),
    dict(service_id="SVC-INET-RES",   name="Internet Residential",  service_type="Internet", region="North", availability_pct=99.7, error_rate_pct=0.8, mttr_hours=2.0),
    dict(service_id="SVC-INET-BIZ",   name="Internet Business",    service_type="Internet", region="South", availability_pct=98.5, error_rate_pct=6.1, mttr_hours=9.3),
    dict(service_id="SVC-4G-NORTH",   name="Mobile 4G North",      service_type="Mobile",   region="North", availability_pct=99.6, error_rate_pct=1.2, mttr_hours=1.5),
    dict(service_id="SVC-4G-SOUTH",   name="Mobile 4G South",      service_type="Mobile",   region="South", availability_pct=99.1, error_rate_pct=2.5, mttr_hours=4.5),
    dict(service_id="SVC-5G-CORE",    name="Mobile 5G Core",       service_type="Mobile",   region="Core",  availability_pct=99.8, error_rate_pct=0.5, mttr_hours=1.0),
    dict(service_id="SVC-IPTV-PRI",   name="IPTV Primary",         service_type="IPTV",     region="North", availability_pct=98.2, error_rate_pct=7.5, mttr_hours=11.0),
    dict(service_id="SVC-IPTV-BAK",   name="IPTV Backup",          service_type="IPTV",     region="South", availability_pct=99.3, error_rate_pct=1.8, mttr_hours=3.0),
    dict(service_id="SVC-VPN-ENT",    name="VPN Enterprise",       service_type="VPN",      region="Core",  availability_pct=97.5, error_rate_pct=8.2, mttr_hours=14.0),
]

async def seed_service_assurance_data():
    async with AsyncSessionLocal() as db:
        count = (await db.execute(select(func.count()).select_from(ServiceEndpoint))).scalar()
        if count and count > 0:
            return
        for svc in _SERVICES:
            db.add(ServiceEndpoint(**svc))
        await db.commit()
