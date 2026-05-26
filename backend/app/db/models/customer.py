from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from sqlalchemy.sql import func
from app.db.database import Base


class CustomerAccount(Base):
    __tablename__ = "customer_accounts"

    id                    = Column(Integer, primary_key=True, index=True)
    account_id            = Column(String,  unique=True, index=True, nullable=False)
    name                  = Column(String,  nullable=False)
    segment               = Column(String)              # Enterprise | SMB | Retail | Government
    region                = Column(String)
    plan                  = Column(String)              # Premium | Standard | Basic
    active_orders         = Column(Integer, default=0)
    order_completion_rate = Column(Float,   default=100.0)  # % — higher is better
    avg_fulfillment_time  = Column(Float,   default=24.0)   # hours — lower is better
    sla_breach_rate       = Column(Float,   default=0.0)    # % — lower is better
    created_at            = Column(DateTime(timezone=True), server_default=func.now())


class CustomerRecord(Base):
    __tablename__ = "customer_records"

    id          = Column(Integer, primary_key=True, index=True)
    session_id  = Column(String, index=True)
    input_data  = Column(Text)
    output_data = Column(Text)
    status      = Column(String, default="pending")
    confidence  = Column(Float,  default=0.0)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())
