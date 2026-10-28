from motor.motor_asyncio import AsyncIOMotorClient

from app.config.settings import settings


class MongoDB:
    client: AsyncIOMotorClient | None = None
    database = None


mongodb = MongoDB()


async def connect_to_mongodb():
    mongodb.client = AsyncIOMotorClient(
        settings.mongodb_uri
    )

    mongodb.database = mongodb.client[
        settings.mongodb_database
    ]

    await mongodb.client.admin.command("ping")

    print(
        f"MongoDB connected: {settings.mongodb_database}"
    )


async def close_mongodb_connection():
    if mongodb.client:
        mongodb.client.close()
        mongodb.client = None
        mongodb.database = None


def get_database():
    if mongodb.database is None:
        raise RuntimeError("MongoDB is not connected")

    return mongodb.database