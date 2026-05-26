from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from sqlalchemy.sql import func
from app.db.database import Base


class NetworkDevice(Base):
    __tablename__ = "network_devices"

    id               = Column(Integer, primary_key=True, index=True)
    name             = Column(String,  nullable=False, index=True)
    type             = Column(String)               # router | switch | olt | bts | core
    region           = Column(String)
    ip_address       = Column(String)
    status           = Column(String, default="healthy")  # healthy | degraded | down
    uptime_pct       = Column(Float,  default=100.0)
    cpu_pct          = Column(Float,  default=0.0)
    memory_pct       = Column(Float,  default=0.0)
    packet_loss_pct  = Column(Float,  default=0.0)
    latency_ms       = Column(Float,  default=0.0)
    last_seen        = Column(DateTime(timezone=True), server_default=func.now())
    created_at       = Column(DateTime(timezone=True), server_default=func.now())


class NetworkLink(Base):
    __tablename__ = "network_links"

    id              = Column(Integer, primary_key=True, index=True)
    source_device   = Column(String, nullable=False)
    dest_device     = Column(String, nullable=False)
    link_type       = Column(String)             # fiber | microwave | copper
    latency_ms      = Column(Float,  default=0.0)
    packet_loss_pct = Column(Float,  default=0.0)
    bandwidth_mbps  = Column(Float,  default=0.0)
    utilization_pct = Column(Float,  default=0.0)
    status          = Column(String, default="ok")   # ok | degraded | down
    last_updated    = Column(DateTime(timezone=True), server_default=func.now())


class NetworkAlert(Base):
    __tablename__ = "network_alerts"

    id          = Column(Integer, primary_key=True, index=True)
    device_name = Column(String,  index=True)
    severity    = Column(String)   # critical | high | medium | low
    category    = Column(String)   # outage | degradation | high_utilization | packet_loss
    message     = Column(Text)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class NetworkRecord(Base):
    __tablename__ = "network_records"

    id          = Column(Integer, primary_key=True, index=True)
    session_id  = Column(String, index=True)
    input_data  = Column(Text)
    output_data = Column(Text)
    status      = Column(String, default="pending")
    confidence  = Column(Float,  default=0.0)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())
