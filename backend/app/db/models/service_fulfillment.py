from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base


class ServiceOrder(Base):
    __tablename__ = "service_orders"

    id              = Column(String,  primary_key=True, index=True)   # e.g. ORD-001
    order_type      = Column(String,  nullable=False)                  # SIM_ACTIVATION | BROADBAND | NUMBER_PORTING
    customer_id     = Column(String,  index=True)
    customer_name   = Column(String)
    status          = Column(String,  default="PENDING")               # PENDING → VALIDATING → PROVISIONING → TESTING → COMPLETED / FAILED
    current_step    = Column(String)                                   # Validate | Allocate Resource | Configure | Activate | Confirm
    failure_reason  = Column(Text,    nullable=True)
    sla_status      = Column(String,  default="ON_TRACK")              # ON_TRACK | AT_RISK | BREACHED
    created_at      = Column(DateTime(timezone=False), default=func.now())
    updated_at      = Column(DateTime(timezone=False), onupdate=func.now())


class ProvisioningStep(Base):
    __tablename__ = "provisioning_steps"

    id              = Column(Integer, primary_key=True, index=True)
    order_id        = Column(String,  ForeignKey("service_orders.id"), index=True)
    step_name       = Column(String)                                   # Validate | Allocate Resource | Configure | Activate | Confirm
    status          = Column(String,  default="PENDING")               # PENDING | RUNNING | COMPLETED | FAILED
    start_time      = Column(DateTime(timezone=False), nullable=True)
    end_time        = Column(DateTime(timezone=False), nullable=True)
    duration_seconds= Column(Float,   nullable=True)
    error_message   = Column(Text,    nullable=True)


class StepMetrics(Base):
    __tablename__ = "step_metrics"

    id                   = Column(Integer, primary_key=True, index=True)
    step_name            = Column(String,  unique=True, index=True)
    avg_duration_seconds = Column(Float,   default=60.0)


class ServicefulfillmentRecord(Base):
    __tablename__ = "service_fulfillment_records"

    id          = Column(Integer, primary_key=True, index=True)
    session_id  = Column(String, index=True)
    input_data  = Column(Text)
    output_data = Column(Text)
    status      = Column(String, default="pending")
    confidence  = Column(Float,  default=0.0)
    created_at  = Column(DateTime(timezone=False), server_default=func.now())
    updated_at  = Column(DateTime(timezone=False), onupdate=func.now())
