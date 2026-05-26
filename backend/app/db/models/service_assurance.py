from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.sql import func
from app.db.database import Base


class ServiceEndpoint(Base):
    __tablename__ = "service_endpoints"

    id              = Column(Integer, primary_key=True, index=True)
    service_id      = Column(String,  unique=True, index=True, nullable=False)
    name            = Column(String,  nullable=False)
    service_type    = Column(String)   # VoIP | Internet | Mobile | IPTV | VPN
    region          = Column(String)
    availability_pct= Column(Float,   default=100.0)  # % — higher is better
    error_rate_pct  = Column(Float,   default=0.0)    # % — lower is better
    mttr_hours      = Column(Float,   default=0.0)    # hours — lower is better
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
