from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.database.mongodb import (
    connect_to_mongodb,
    close_mongodb_connection,
)
from app.queue.rabbitmq import rabbitmq_producer
from app.routes.apollo import router as apollo_router
from app.routes.clay import router as clay_router
from app.routes.google_maps import router as google_maps_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(">>> 1. LIFESPAN STARTED", flush=True)

    await connect_to_mongodb()

    print(">>> 2. MONGODB CONNECTED", flush=True)
    print(">>> 3. CONNECTING TO RABBITMQ", flush=True)
    await rabbitmq_producer.connect()
    print(">>> 4. RABBITMQ CONNECTED", flush=True)
    yield
    print(">>> 5. SHUTTING DOWN", flush=True)

    # Close RabbitMQ
    await rabbitmq_producer.close()
    print(">>> 6. RABBITMQ CLOSED", flush=True)

    # Close MongoDB
    await close_mongodb_connection()

    print(">>> 7. MONGODB CLOSED", flush=True)

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5180",
        "http://127.0.0.1:5180",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": settings.app_name,
    }

app.include_router(apollo_router)
app.include_router(clay_router)
app.include_router(google_maps_router)