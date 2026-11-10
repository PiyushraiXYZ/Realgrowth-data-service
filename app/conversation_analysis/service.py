
import logging
from datetime import datetime, timezone

from fastapi import UploadFile

from app.storage.cloudinary_service import cloudinary_storage
from app.conversation_analysis.repository import ConversationRepository
from app.conversation_analysis.models import build_conversation_document
from app.conversation_analysis.image_processor import groq_ocr_service

logger = logging.getLogger(__name__)


class ConversationService:

    def __init__(self):
        self.repository = ConversationRepository()

    async def upload_screenshots(
        self,
        prospect_id: str,
        files: list[UploadFile],
    ) -> dict:
        """Upload screenshots, save conversation and automatically run OCR."""

        if not files:
            raise ValueError("Please upload at least one screenshot.")

        if len(files) > 10:
            raise ValueError("Maximum 10 screenshots allowed per upload.")

        allowed_types = {
            "image/jpeg",
            "image/png",
            "image/webp",
        }

        for file in files:
            if file.content_type not in allowed_types:
                raise ValueError(
                    f"Unsupported image format: {file.filename}"
                )

        uploaded_images = []
        database_saved = False

        try:
            # 1. Upload images to Cloudinary.
            for file in files:
                image_data = await cloudinary_storage.upload_image(
                    file=file
                )

                uploaded_images.append({
                    **image_data,
                    "filename": file.filename,
                })

            # 2. Build conversation document.
            document = build_conversation_document(
                prospect_id=prospect_id,
                screenshots=uploaded_images,
            )

            document["status"] = "OCR_PENDING"
            document["analysis_status"] = "PENDING"

            # 3. Save in MongoDB.
            conversation = await self.repository.create_conversation(
                document
            )
            database_saved = True

            conversation_id = conversation["conversation_id"]

            # 4. Automatically execute OCR.
            try:
                return await self.process_conversation_ocr(
                    conversation_id=conversation_id
                )

            except Exception:
                logger.exception(
                    "Automatic OCR failed for conversation %s",
                    conversation_id,
                )

                await self.repository.update_ocr_status(
                    conversation_id=conversation_id,
                    status="OCR_FAILED",
                )

                return await self.repository.get_conversation(
                    conversation_id
                )

        except Exception:
            logger.exception(
                "Failed to upload screenshots for prospect %s",
                prospect_id,
            )

            # Only delete Cloudinary images if DB save failed.
            if not database_saved:
                for image in uploaded_images:
                    try:
                        await cloudinary_storage.delete_image(
                            image["public_id"]
                        )
                    except Exception:
                        logger.exception(
                            "Cloudinary cleanup failed: %s",
                            image["public_id"],
                        )

            raise

    async def get_conversation(
        self,
        conversation_id: str,
    ) -> dict:
        """Retrieve conversation details from MongoDB."""

        conversation = await self.repository.get_conversation(
            conversation_id
        )

        if not conversation:
            raise ValueError("Conversation not found.")

        return conversation

    async def get_all_conversations(
        self,
        prospect_id: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[dict]:
        """Retrieve conversations with optional prospect filtering."""

        if skip < 0:
            raise ValueError("Skip cannot be negative.")

        if not 1 <= limit <= 100:
            raise ValueError("Limit must be between 1 and 100.")

        return await self.repository.get_all_conversations(
            prospect_id=prospect_id,
            skip=skip,
            limit=limit,
        )

    async def process_conversation_ocr(
        self,
        conversation_id: str,
    ) -> dict:
        """Extract text from all screenshots and save OCR results."""

        conversation = await self.repository.get_conversation(
            conversation_id
        )

        if not conversation:
            raise ValueError("Conversation not found.")

        screenshots = conversation.get("screenshots", [])

        if not screenshots:
            raise ValueError("No screenshots found in this conversation.")

        extracted_messages = []

        for index, screenshot in enumerate(screenshots, start=1):
            image_url = screenshot.get("image_url")

            if not image_url:
                raise ValueError(
                    f"Screenshot {index} does not contain an image URL."
                )

            extracted_text = await groq_ocr_service.extract_text(
                image_url=image_url
            )

            extracted_messages.append({
                "screenshot_index": index,
                "filename": screenshot.get("filename"),
                "public_id": screenshot.get("public_id"),
                "extracted_text": extracted_text,
                "extracted_at": datetime.now(timezone.utc),
            })

        updated_conversation = await self.repository.update_ocr_results(
            conversation_id=conversation_id,
            extracted_messages=extracted_messages,
        )

        if not updated_conversation:
            raise ValueError("Failed to save OCR results.")

        logger.info(
            "OCR completed successfully for conversation %s",
            conversation_id,
        )

        return updated_conversation


conversation_service = ConversationService()
