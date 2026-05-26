from datetime import datetime, timedelta
from sqlalchemy import select, func
from app.db.database import AsyncSessionLocal
from app.db.models.network import NetworkDevice, NetworkLink, NetworkAlert

_DEVICES = [
    dict(name="Core-Router-01",  type="core",   region="North", ip_address="10.0.0.1",  status="healthy",  uptime_pct=99.9, cpu_pct=15.2, memory_pct=45.0, packet_loss_pct=0.1, latency_ms=12.0),
    dict(name="Core-Router-02",  type="core",   region="South", ip_address="10.0.0.2",  status="degraded", uptime_pct=97.3, cpu_pct=92.1, memory_pct=88.0, packet_loss_pct=5.8, latency_ms=320.0),
    dict(name="Edge-Router-N",   type="router", region="North", ip_address="10.1.0.1",  status="healthy",  uptime_pct=99.5, cpu_pct=34.5, memory_pct=52.0, packet_loss_pct=0.3, latency_ms=25.0),
    dict(name="Edge-Router-S",   type="router", region="South", ip_address="10.1.0.2",  status="healthy",  uptime_pct=99.8, cpu_pct=28.3, memory_pct=41.0, packet_loss_pct=0.2, latency_ms=18.0),
    dict(name="Edge-Router-E",   type="router", region="East",  ip_address="10.1.0.3",  status="degraded", uptime_pct=98.1, cpu_pct=67.8, memory_pct=73.0, packet_loss_pct=2.4, latency_ms=145.0),
    dict(name="Edge-Router-W",   type="router", region="West",  ip_address="10.1.0.4",  status="down",     uptime_pct=72.4, cpu_pct=0.0,  memory_pct=0.0,  packet_loss_pct=100.0, latency_ms=0.0),
    dict(name="Switch-North-01", type="switch", region="North", ip_address="10.2.0.1",  status="healthy",  uptime_pct=99.9, cpu_pct=12.4, memory_pct=38.0, packet_loss_pct=0.0, latency_ms=8.0),
    dict(name="Switch-South-01", type="switch", region="South", ip_address="10.2.0.2",  status="healthy",  uptime_pct=99.7, cpu_pct=18.7, memory_pct=43.0, packet_loss_pct=0.1, latency_ms=10.0),
    dict(name="BTS-North-01",    type="bts",    region="North", ip_address="10.3.0.1",  status="healthy",  uptime_pct=99.2, cpu_pct=45.2, memory_pct=60.0, packet_loss_pct=1.2, latency_ms=78.0),
    dict(name="BTS-South-01",    type="bts",    region="South", ip_address="10.3.0.2",  status="healthy",  uptime_pct=99.4, cpu_pct=38.9, memory_pct=55.0, packet_loss_pct=0.8, latency_ms=65.0),
    dict(name="BTS-East-01",     type="bts",    region="East",  ip_address="10.3.0.3",  status="degraded", uptime_pct=96.8, cpu_pct=71.3, memory_pct=78.0, packet_loss_pct=2.4, latency_ms=155.0),
    dict(name="BTS-West-01",     type="bts",    region="West",  ip_address="10.3.0.4",  status="healthy",  uptime_pct=98.9, cpu_pct=55.1, memory_pct=62.0, packet_loss_pct=1.5, latency_ms=90.0),
    # Monitored devices per outage-monitoring spec
    dict(name="Router-01",  type="router", region="North", ip_address="10.10.0.1", status="healthy",  uptime_pct=99.8, cpu_pct=35.0, memory_pct=42.0, packet_loss_pct=0.5,  latency_ms=45.0),
    dict(name="Router-02",  type="router", region="South", ip_address="10.10.0.2", status="down",     uptime_pct=88.1, cpu_pct=93.0, memory_pct=91.0, packet_loss_pct=6.2,  latency_ms=340.0),
    dict(name="Router-03",  type="router", region="East",  ip_address="10.10.0.3", status="degraded", uptime_pct=97.5, cpu_pct=75.0, memory_pct=68.0, packet_loss_pct=3.1,  latency_ms=155.0),
    dict(name="Switch-01",  type="switch", region="North", ip_address="10.10.1.1", status="healthy",  uptime_pct=99.9, cpu_pct=28.0, memory_pct=35.0, packet_loss_pct=0.2,  latency_ms=22.0),
    dict(name="Switch-02",  type="switch", region="South", ip_address="10.10.1.2", status="degraded", uptime_pct=98.3, cpu_pct=72.0, memory_pct=60.0, packet_loss_pct=2.1,  latency_ms=115.0),
    dict(name="OLT-01",     type="olt",    region="North", ip_address="10.10.2.1", status="healthy",  uptime_pct=99.7, cpu_pct=40.0, memory_pct=50.0, packet_loss_pct=0.8,  latency_ms=60.0),
    dict(name="OLT-02",     type="olt",    region="East",  ip_address="10.10.2.2", status="degraded", uptime_pct=95.2, cpu_pct=91.0, memory_pct=85.0, packet_loss_pct=4.8,  latency_ms=285.0),
    dict(name="BTS-North",  type="bts",    region="North", ip_address="10.10.3.1", status="healthy",  uptime_pct=99.5, cpu_pct=55.0, memory_pct=58.0, packet_loss_pct=1.5,  latency_ms=88.0),
    dict(name="BTS-South",  type="bts",    region="South", ip_address="10.10.3.2", status="healthy",  uptime_pct=99.1, cpu_pct=68.0, memory_pct=65.0, packet_loss_pct=1.0,  latency_ms=95.0),
    dict(name="BTS-East",   type="bts",    region="East",  ip_address="10.10.3.3", status="down",     uptime_pct=91.4, cpu_pct=88.0, memory_pct=82.0, packet_loss_pct=7.5,  latency_ms=380.0),
]

_LINKS = [
    dict(source_device="Core-Router-01", dest_device="Edge-Router-N",  link_type="fiber",     latency_ms=2.1, packet_loss_pct=0.0,   bandwidth_mbps=10000, utilization_pct=35.0, status="ok"),
    dict(source_device="Core-Router-01", dest_device="Edge-Router-S",  link_type="fiber",     latency_ms=3.4, packet_loss_pct=0.1,   bandwidth_mbps=10000, utilization_pct=42.0, status="ok"),
    dict(source_device="Core-Router-01", dest_device="Edge-Router-E",  link_type="fiber",     latency_ms=5.2, packet_loss_pct=0.8,   bandwidth_mbps=10000, utilization_pct=67.0, status="degraded"),
    dict(source_device="Core-Router-01", dest_device="Edge-Router-W",  link_type="fiber",     latency_ms=0.0, packet_loss_pct=100.0, bandwidth_mbps=10000, utilization_pct=0.0,  status="down"),
    dict(source_device="Core-Router-02", dest_device="Edge-Router-S",  link_type="fiber",     latency_ms=2.8, packet_loss_pct=0.2,   bandwidth_mbps=10000, utilization_pct=89.0, status="degraded"),
    dict(source_device="Edge-Router-N",  dest_device="BTS-North-01",   link_type="microwave", latency_ms=1.5, packet_loss_pct=0.0,   bandwidth_mbps=1000,  utilization_pct=48.0, status="ok"),
    dict(source_device="Edge-Router-S",  dest_device="BTS-South-01",   link_type="microwave", latency_ms=1.8, packet_loss_pct=0.1,   bandwidth_mbps=1000,  utilization_pct=52.0, status="ok"),
    dict(source_device="Edge-Router-E",  dest_device="BTS-East-01",    link_type="microwave", latency_ms=4.2, packet_loss_pct=2.4,   bandwidth_mbps=1000,  utilization_pct=78.0, status="degraded"),
]

_ALERTS = [
    dict(device_name="Edge-Router-W",  severity="critical", category="outage",           message="Edge-Router-W is completely unreachable — full outage in West region. 0% uptime. Possible fiber cut or power failure."),
    dict(device_name="Core-Router-02", severity="critical", category="high_utilization", message="Core-Router-02 CPU at 92.1% — critically near failure threshold. Immediate traffic redistribution required."),
    dict(device_name="Edge-Router-E",  severity="high",     category="degradation",      message="Edge-Router-E CPU 67.8%, memory 73%. East region experiencing elevated latency and packet loss on uplink."),
    dict(device_name="BTS-East-01",    severity="high",     category="packet_loss",      message="BTS-East-01 uplink showing 2.4% packet loss (threshold: 1%). East mobile subscribers experiencing call drops."),
    dict(device_name="Core-Router-02", severity="medium",   category="high_utilization", message="Core-Router-02 memory at 88% — risk of swap usage causing latency degradation. Schedule maintenance window."),
]


async def seed_network_data():
    async with AsyncSessionLocal() as db:
        count = (await db.execute(select(func.count()).select_from(NetworkDevice))).scalar()
        if count and count > 0:
            return

        now = datetime.utcnow()
        for d in _DEVICES:
            db.add(NetworkDevice(**d))
        for lk in _LINKS:
            db.add(NetworkLink(**lk))
        for i, al in enumerate(_ALERTS):
            db.add(NetworkAlert(**al, created_at=now - timedelta(minutes=120 - i * 20)))

        await db.commit()
