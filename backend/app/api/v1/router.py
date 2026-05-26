from fastapi import APIRouter
from app.api.v1.endpoints import (
    orchestrator, network, customer,
    service_fulfillment, service_assurance,
    billing, call, social_media,
)

api_router = APIRouter()
api_router.include_router(orchestrator.router,        prefix="/orchestrator",        tags=["Orchestrator"])
api_router.include_router(network.router,             prefix="/network",             tags=["Network"])
api_router.include_router(customer.router,            prefix="/customer",            tags=["Customer"])
api_router.include_router(service_fulfillment.router, prefix="/service-fulfillment", tags=["Service Fulfillment"])
api_router.include_router(service_assurance.router,   prefix="/service-assurance",   tags=["Service Assurance"])
api_router.include_router(billing.router,             prefix="/billing",             tags=["Billing"])
api_router.include_router(call.router,                prefix="/call",                tags=["Call"])
api_router.include_router(social_media.router,        prefix="/social-media",        tags=["Social Media"])
