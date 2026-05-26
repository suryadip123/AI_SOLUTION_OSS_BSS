from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.sql import func
from app.db.database import Base


class SocialChannel(Base):
    __tablename__ = "social_channels"

    id                  = Column(Integer, primary_key=True, index=True)
    channel_id          = Column(String,  unique=True, index=True, nullable=False)
    platform            = Column(String,  nullable=False)
    nps_score           = Column(Float,   default=50.0)   # -100 to 100 — higher is better
    negative_sentiment  = Column(Float,   default=0.0)    # % — lower is better
    complaint_volume    = Column(Float,   default=0.0)    # per day — lower is better
    total_mentions      = Column(Integer, default=0)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())


class SocialmediaRecord(Base):
    __tablename__ = "social_media_records"

    id          = Column(Integer, primary_key=True, index=True)
    session_id  = Column(String, index=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
