
from datetime import datetime, timezone

from pymongo import ReturnDocument

from app.config.settings import settings
from app.database.mongodb import get_database


class ConversationRepository:

    @property
    def collection(self):
        return get_database()[
            settings.mongodb_conversation_collection
        ]

    async def create_indexes(self):
        await self.collection.create_index(
            "conversation_id",
            unique=True
        )

        await self.collection.create_index("prospect_id")

        await self.collection.create_index(
            [("created_at", -1)]
        )

    async def create_conversation(self, document: dict):
        result = await self.collection.insert_one(document)

        created_document = await self.collection.find_one(
            {"_id": result.inserted_id},
            {"_id": 0}
        )

        if not created_document:
            raise ValueError("Failed to retrieve conversation.")

        return created_document

    async def get_conversation(
        self,
        conversation_id: str
    ) -> dict | None:
        return await self.collection.find_one(
            {"conversation_id": conversation_id},
            {"_id": 0}
        )

    async def get_all_conversations(
        self,
        prospect_id: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[dict]:

        query = {}

        if prospect_id:
            query["prospect_id"] = prospect_id

        cursor = (
            self.collection
            .find(query, {"_id": 0})
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )

        return await cursor.to_list(length=limit)

    async def update_ocr_results(
        self,
        conversation_id: str,
        extracted_messages: list[dict],
    ) -> dict | None:

        result = await self.collection.find_one_and_update(
            {"conversation_id": conversation_id},
            {
                "$set": {
                    "extracted_messages": extracted_messages,
                    "status": "OCR_COMPLETED",
                    "analysis_status": "PENDING",
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )

        return result

    
    async def update_ocr_status(
     self,
     conversation_id: str,
     status: str,
     ) -> bool:
     result = await self.collection.update_one(
        {"conversation_id": conversation_id},
        {
            "$set": {
                "status": status,
                "updated_at": datetime.now(timezone.utc),
            }
        },
     )

     return result.modified_count > 0 or result.matched_count > 0

