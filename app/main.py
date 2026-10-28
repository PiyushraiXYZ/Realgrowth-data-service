from fastapi import FastAPI

from app.config.settings import settings
from app.routes.apollo import router as apollo_router
from app.routes.clay import router as clay_router
from app.routes.google_maps import router as google_maps_router

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


# Register API routers
app.include_router(apollo_router)
app.include_router(clay_router)
app.include_router(google_maps_router)