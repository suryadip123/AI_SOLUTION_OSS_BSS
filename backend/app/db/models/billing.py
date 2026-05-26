from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.sql import func
from app.db.database import Base


class BillingAccount(Base):
    __tablename__ = "billing_accounts"

    id                    = Column(Integer, primary_key=True, index=True)
    account_id            = Column(String,  unique=True, index=True, nullable=False)
    name                  = Column(String,  nullable=False)
    segment               = Column(String)   # Enterprise | SMB | Retail | Government
    region                = Column(String)
    bill_gen_success_rate = Column(Float,   default=100.0)  # % — higher is better
    payment_collection_rate = Column(Float, default=100.0)  # % — higher is better
    dispute_rate          = Column(Float,   default=0.0)    # % — lower is better
    total_bills           = Column(Integer, default=0)
    created_at            = Column(DateTime(timezone=True), server_default=func.now())


class BillingRecord(Base):
    __tablename__ = "billing_records"

    id          = Column(Integer, primary_key=True, index=True)
    session_id  = Column(String, index=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
