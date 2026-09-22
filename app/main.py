from fastapi import FastAPI

from app.config import settings
from app.api.routes import customer_router, orders_router, billing_router, support_router

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)

app.include_router(customer_router)
app.include_router(orders_router)
app.include_router(billing_router)
app.include_router(support_router)

@app.get("/")
async def root():
    return {
        "service": settings.app_name,
        "status": "running",
        "environment": settings.app_env,
    }



@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }