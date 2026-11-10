
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
from app.connection_tracking.router import router as connection_router
from app.connection_tracking.repository import ConnectionRepository
from app.conversation_analysis.router import router as conversation_router
from app.conversation_analysis.repository import ConversationRepository

@asynccontextmanager
async def lifespan(app: FastAPI):

    print(">>> 1. LIFESPAN STARTED", flush=True)

    # Connect to MongoDB
    await connect_to_mongodb()
    print(">>> 2. MONGODB CONNECTED", flush=True)

    # Initialize Connection Tracking indexes
    connection_repository = ConnectionRepository()
    await connection_repository.create_indexes()
    print(">>> 3. CONNECTION TRACKING INDEXES CREATED", flush=True)

    # Connect to RabbitMQ
    print(">>> 4. CONNECTING TO RABBITMQ", flush=True)
    await rabbitmq_producer.connect()
    print(">>> 5. RABBITMQ CONNECTED", flush=True)

    yield

    print(">>> 6. SHUTTING DOWN", flush=True)

    # Close RabbitMQ
    await rabbitmq_producer.close()
    print(">>> 7. RABBITMQ CLOSED", flush=True)

    # Close MongoDB
    await close_mongodb_connection()
    print(">>> 8. MONGODB CLOSED", flush=True)


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)


# CORS Configuration
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


# Health Check
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": settings.app_name,
    }


# Existing Provider Routes
app.include_router(apollo_router)
app.include_router(clay_router)
app.include_router(google_maps_router)

# Prospect Connection Tracking Routes
app.include_router(connection_router)

# Conversational Analysis Routes
app.include_router(conversation_router)
