from fastapi import FastAPI

from app.config.settings import settings
from app.routes.apollo import router as apollo_router


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": settings.app_name,
    }


app.include_router(apollo_router)