from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from sqlalchemy.sql import func
from app.db.database import Base

class SocialmediaRecord(Base):
    __tablename__ = "social_media_records"

    id          = Column(Integer, primary_key=True, index=True)
    session_id  = Column(String, index=True)
    input_data  = Column(Text)
    output_data = Column(Text)
    status      = Column(String, default="pending")
    confidence  = Column(Float, default=0.0)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())
