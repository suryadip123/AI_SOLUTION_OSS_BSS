from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.api.v1.router import api_router
from app.db.database import init_db
import app.db.models.network   # noqa: F401
import app.db.models.customer  # noqa: F401

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

app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}
