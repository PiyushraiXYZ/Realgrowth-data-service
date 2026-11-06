
from datetime import datetime, timezone

from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.config.settings import settings
from app.database.mongodb import get_database


class ConnectionRepository:

    def __init__(self):
        self.collection = None

    @property
    def connections(self):
        if self.collection is None:
            database = get_database()
            self.collection = database[
                settings.mongodb_connection_collection
            ]

        return self.collection

    async def create_indexes(self) -> None:
        """
        Create indexes for connection tracking.
        """

        await self.connections.create_index(
            [("connection_id", ASCENDING)],
            unique=True,
            name="unique_connection_id"
        )

        await self.connections.create_index(
            [
                ("prospect_id", ASCENDING),
                ("platform", ASCENDING)
            ],
            unique=True,
            name="unique_prospect_platform"
        )

        await self.connections.create_index(
            [("processed_event_ids", ASCENDING)],
            name="connection_event_lookup"
        )

        await self.connections.create_index(
            [
                ("prospect_id", ASCENDING),
                ("created_at", DESCENDING)
            ],
            name="prospect_connection_history"
        )

    async def create_connection(self, document: dict) -> dict:
        """
        Create a new connection record.
        """

        try:
            result = await self.connections.insert_one(document)

            created_document = await self.connections.find_one(
                {"_id": result.inserted_id},
                {"_id": 0}
            )

            if not created_document:
                raise ValueError("Failed to retrieve created connection")

            return created_document

        except DuplicateKeyError as exc:
            raise ValueError(
                "A connection already exists for this prospect and platform."
            ) from exc


    async def get_connection_by_id(
        self,
        connection_id: str
    ) -> dict | None:

        return await self.connections.find_one(
            {"connection_id": connection_id},
            {"_id": 0}
        )

    async def get_connection_by_prospect(
        self,
        prospect_id: str,
        platform: str
    ) -> dict | None:

        return await self.connections.find_one(
            {
                "prospect_id": prospect_id,
                "platform": platform
            },
            {"_id": 0}
        )

    async def get_connections_by_prospect(
        self,
        prospect_id: str
    ) -> list[dict]:

        cursor = self.connections.find(
            {"prospect_id": prospect_id},
            {"_id": 0}
        ).sort("created_at", DESCENDING)

        return await cursor.to_list(length=100)

    async def update_connection_status(
        self,
        connection_id: str,
        status: str,
        event_id: str,
        source: str,
        notes: str | None = None,
        occurred_at: datetime | None = None,
    ) -> dict | None:
        """
        Update connection status and append event history.

        Duplicate event IDs are not processed again.
        """

        timestamp = occurred_at or datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)

        update = await self.connections.find_one_and_update(
            {
                "connection_id": connection_id,
                "processed_event_ids": {"$ne": event_id}
            },
            {
                "$set": {
                    "current_status": status,
                    "updated_at": updated_at
                },
                "$push": {
                    "history": {
                        "event_id": event_id,
                        "status": status,
                        "source": source,
                        "timestamp": timestamp,
                        "notes": notes
                    },
                    "processed_event_ids": event_id
                }
            },
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0}
        )

        if update is not None:
            return update

        existing = await self.get_connection_by_id(connection_id)

        if existing is None:
            raise ValueError("Connection not found")

        if event_id in existing.get("processed_event_ids", []):
            raise ValueError("Event already processed")

        raise ValueError(
            "Connection update could not be completed."
        )
