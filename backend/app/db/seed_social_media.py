from sqlalchemy import select, func
from app.db.database import AsyncSessionLocal
from app.db.models.social_media import SocialChannel

_CHANNELS = [
    dict(channel_id="SM-TWITTER",  platform="Twitter / X",     nps_score=45.0,  negative_sentiment=15.0, complaint_volume=30.0,  total_mentions=8500),
    dict(channel_id="SM-FACEBOOK", platform="Facebook",        nps_score=52.0,  negative_sentiment=12.0, complaint_volume=20.0,  total_mentions=12000),
    dict(channel_id="SM-INSTA",    platform="Instagram",       nps_score=38.0,  negative_sentiment=18.0, complaint_volume=35.0,  total_mentions=9200),
    dict(channel_id="SM-LINKEDIN", platform="LinkedIn",        nps_score=61.0,  negative_sentiment=8.0,  complaint_volume=10.0,  total_mentions=4100),
    dict(channel_id="SM-YOUTUBE",  platform="YouTube",         nps_score=25.0,  negative_sentiment=24.0, complaint_volume=55.0,  total_mentions=6700),
    dict(channel_id="SM-GOOGLE",   platform="Google Reviews",  nps_score=-5.0,  negative_sentiment=48.0, complaint_volume=120.0, total_mentions=3200),
    dict(channel_id="SM-TRUST",    platform="Trustpilot",      nps_score=18.0,  negative_sentiment=28.0, complaint_volume=75.0,  total_mentions=2800),
    dict(channel_id="SM-REDDIT",   platform="Reddit",          nps_score=5.0,   negative_sentiment=42.0, complaint_volume=90.0,  total_mentions=5500),
    dict(channel_id="SM-APPSTORE", platform="App Store",       nps_score=33.0,  negative_sentiment=20.0, complaint_volume=45.0,  total_mentions=7800),
    dict(channel_id="SM-PLAY",     platform="Play Store",      nps_score=-8.0,  negative_sentiment=45.0, complaint_volume=110.0, total_mentions=9100),
]

async def seed_social_media_data():
    async with AsyncSessionLocal() as db:
        count = (await db.execute(select(func.count()).select_from(SocialChannel))).scalar()
        if count and count > 0:
            return
        for ch in _CHANNELS:
            db.add(SocialChannel(**ch))
        await db.commit()
