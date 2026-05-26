from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.sql import func
from app.db.database import Base


class CallGateway(Base):
    __tablename__ = "call_gateways"

    id                = Column(Integer, primary_key=True, index=True)
    gateway_id        = Column(String,  unique=True, index=True, nullable=False)
    region            = Column(String)
    call_success_rate = Column(Float,   default=100.0)  # % — higher is better
    call_drop_rate    = Column(Float,   default=0.0)    # % — lower is better
    avg_duration_min  = Column(Float,   default=5.0)    # minutes — lower can indicate drops
    total_calls       = Column(Integer, default=0)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())


class CallRecord(Base):
    __tablename__ = "call_records"

    id          = Column(Integer, primary_key=True, index=True)
    session_id  = Column(String, index=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
