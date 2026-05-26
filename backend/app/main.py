from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.api.v1.router import api_router
from app.db.database import init_db
import app.db.models.network              # noqa: F401
import app.db.models.customer             # noqa: F401
import app.db.models.service_fulfillment  # noqa: F401
import app.db.models.service_assurance    # noqa: F401
import app.db.models.billing              # noqa: F401
import app.db.models.call                 # noqa: F401
import app.db.models.social_media         # noqa: F401

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    await init_db()
    from app.db.seed_network import seed_network_data
    await seed_network_data()
    from app.db.seed_customer import seed_customer_data
    await seed_customer_data()
    from app.db.seed_service_fulfillment import seed_service_fulfillment_data
    await seed_service_fulfillment_data()
    from app.db.seed_service_assurance import seed_service_assurance_data
    await seed_service_assurance_data()
    from app.db.seed_billing import seed_billing_data
    await seed_billing_data()
    from app.db.seed_call import seed_call_data
    await seed_call_data()
    from app.db.seed_social_media import seed_social_media_data
    await seed_social_media_data()

app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}
