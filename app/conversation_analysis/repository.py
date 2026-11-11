
import logging
from datetime import datetime, timezone

from pymongo import ReturnDocument

from app.config.settings import settings
from app.database.mongodb import get_database

logger = logging.getLogger(__name__)


class ConversationRepository:

    @property
    def collection(self):
        return get_database()[
            settings.mongodb_conversation_collection
        ]

    async def create_indexes(self):
        """Create indexes for conversation queries."""

        await self.collection.create_index(
            "conversation_id",
            unique=True,
        )

        await self.collection.create_index("prospect_id")

        await self.collection.create_index(
            [("created_at", -1)]
        )

    async def create_conversation(self, document: dict) -> dict:
        """Insert a new conversation document."""

        result = await self.collection.insert_one(document)

        created_document = await self.collection.find_one(
            {"_id": result.inserted_id},
            {"_id": 0},
        )

        if not created_document:
            raise ValueError("Failed to create conversation.")

        return created_document

    async def get_conversation(
        self,
        conversation_id: str,
    ) -> dict | None:
        """Retrieve one conversation by ID."""

        return await self.collection.find_one(
            {"conversation_id": conversation_id},
            {"_id": 0},
        )

    async def get_all_conversations(
        self,
        prospect_id: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[dict]:
        """Retrieve conversations with optional prospect filtering."""

        query = {}

        if prospect_id:
            query["prospect_id"] = prospect_id

        cursor = (
            self.collection
            .find(
                query,
                {
                    "_id": 0,
                    "conversation_id": 1,
                    "prospect_id": 1,
                    "status": 1,
                    "analysis_status": 1,
                    "created_at": 1,
                },
            )
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )

        return await cursor.to_list(length=limit)

    async def update_ocr_results(
        self,
        conversation_id: str,
        extracted_messages: list[dict],
        reconstructed_conversation: dict,
    ) -> dict | None:
        """Save OCR, layout and reconstructed conversation results."""

        return await self.collection.find_one_and_update(
            {"conversation_id": conversation_id},
            {
                "$set": {
                    "extracted_messages": extracted_messages,
                    "reconstructed_conversation": (
                        reconstructed_conversation
                    ),
                    "status": "RECONSTRUCTION_COMPLETED",
                    "analysis_status": "PENDING",
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )

    async def update_ocr_status(
        self,
        conversation_id: str,
        status: str,
    ) -> bool:
        """Update OCR or reconstruction processing status."""

        result = await self.collection.update_one(
            {"conversation_id": conversation_id},
            {
                "$set": {
                    "status": status,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

        return result.matched_count > 0

    async def update_analysis_status(
        self,
        conversation_id: str,
        status: str,
    ) -> bool:
        """Update LLM analysis processing status."""

        result = await self.collection.update_one(
            {"conversation_id": conversation_id},
            {
                "$set": {
                    "analysis_status": status,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

        return result.matched_count > 0

    async def update_analysis_result(
        self,
        conversation_id: str,
        analysis_result: dict,
    ) -> bool:
        """Save the completed LLM analysis result."""

        result = await self.collection.update_one(
            {"conversation_id": conversation_id},
            {
                "$set": {
                    "analysis": analysis_result,
                    "analysis_status": "COMPLETED",
                    "status": "COMPLETED",
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

        return result.matched_count > 0


conversation_repository = ConversationRepository()
