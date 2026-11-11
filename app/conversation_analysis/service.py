
import logging

from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from app.conversation_analysis.models import (
    build_conversation_document,
)
from app.conversation_analysis.repository import (
    ConversationRepository,
)
from app.conversation_analysis.tasks import (
    process_conversation_task,
)
from app.storage.cloudinary_service import cloudinary_storage


logger = logging.getLogger(__name__)


class ConversationService:

    def __init__(self):
        self.repository = ConversationRepository()

    @staticmethod
    def _build_api_response(conversation: dict) -> dict:
        """
        Build a clean API response without exposing internal
        OCR, layout, screenshot, or Cloudinary metadata.
        """

        reconstructed = (
            conversation.get("reconstructed_conversation") or {}
        )

        messages = reconstructed.get("messages", [])

        extracted_text = []

        for index, message in enumerate(messages, start=1):
            extracted_text.append({
                "sequence": message.get("sequence", index),
                "sender": message.get("sender"),
                "timestamp": message.get("timestamp"),
                "date": message.get("date"),
                "text": message.get("text", ""),
            })

        return {
            "conversation_id": conversation["conversation_id"],
            "status": conversation.get("status", "UNKNOWN"),
            "analysis_status": conversation.get(
                "analysis_status",
                "PENDING",
            ),
            "extracted_text": extracted_text,
            "analysis_result": conversation.get("analysis"),
        }

    async def upload_screenshots(
        self,
        prospect_id: str,
        files: list[UploadFile],
    ) -> dict:
        """
        Upload screenshots to Cloudinary, create a MongoDB
        conversation document, and enqueue background processing.

        OCR, reconstruction, and LLM analysis are handled by Celery.
        """

        # -------------------------------------------------
        # STEP 1: Validate request
        # -------------------------------------------------

        if not prospect_id or not prospect_id.strip():
            raise ValueError("Prospect ID is required.")

        prospect_id = prospect_id.strip()

        if not files:
            raise ValueError(
                "Please upload at least one screenshot."
            )

        if len(files) > 10:
            raise ValueError(
                "Maximum 10 screenshots allowed."
            )

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
        conversation_id = None

        try:

            # -------------------------------------------------
            # STEP 2: Upload screenshots to Cloudinary
            # -------------------------------------------------

            for file in files:

                image_data = await cloudinary_storage.upload_image(
                    file=file,
                )

                uploaded_images.append({
                    **image_data,
                    "filename": file.filename,
                })

            logger.info(
                "Screenshots uploaded to Cloudinary | "
                "prospect_id=%s | count=%s",
                prospect_id,
                len(uploaded_images),
            )

            # -------------------------------------------------
            # STEP 3: Create MongoDB conversation document
            # -------------------------------------------------

            document = build_conversation_document(
                prospect_id=prospect_id,
                screenshots=uploaded_images,
            )

            document["status"] = "QUEUED"
            document["analysis_status"] = "PENDING"

            conversation = await self.repository.create_conversation(
                document
            )

            database_saved = True

            conversation_id = conversation["conversation_id"]

            logger.info(
                "Conversation created | conversation_id=%s",
                conversation_id,
            )

            # -------------------------------------------------
            # STEP 4: Submit background task to Celery
            # -------------------------------------------------

            try:

                task = await run_in_threadpool(
                    process_conversation_task.apply_async,
                    args=[conversation_id],
                )

            except Exception:

                logger.exception(
                    "Failed to enqueue Celery task | "
                    "conversation_id=%s",
                    conversation_id,
                )

                await self.repository.update_ocr_status(
                    conversation_id=conversation_id,
                    status="QUEUE_FAILED",
                )

                raise RuntimeError(
                    "Screenshots were uploaded successfully, "
                    "but background processing could not be scheduled."
                )

            logger.info(
                "Conversation task queued successfully | "
                "conversation_id=%s | task_id=%s",
                conversation_id,
                task.id,
            )

            # -------------------------------------------------
            # STEP 5: Return immediately
            # -------------------------------------------------

            return {
                "conversation_id": conversation_id,
                "task_id": task.id,
                "status": "QUEUED",
                "analysis_status": "PENDING",
                "message": (
                    "Screenshots uploaded successfully. "
                    "Conversation processing has been queued."
                ),
            }

        except Exception:

            logger.exception(
                "Screenshot upload failed | prospect_id=%s",
                prospect_id,
            )

            # -------------------------------------------------
            # STEP 6: Cloudinary cleanup
            # Only clean up if MongoDB document was not created.
            # -------------------------------------------------

            if not database_saved:

                for image in uploaded_images:

                    public_id = image.get("public_id")

                    if not public_id:
                        continue

                    try:

                        await cloudinary_storage.delete_image(
                            public_id=public_id,
                        )

                        logger.info(
                            "Cloudinary image cleanup completed | "
                            "public_id=%s",
                            public_id,
                        )

                    except Exception:

                        logger.exception(
                            "Cloudinary cleanup failed | public_id=%s",
                            public_id,
                        )

            raise

    async def get_conversation(
        self,
        conversation_id: str,
    ) -> dict:
        """
        Retrieve one conversation with extracted messages
        and its current LLM analysis result.
        """

        conversation = await self.repository.get_conversation(
            conversation_id=conversation_id,
        )

        if not conversation:
            raise ValueError("Conversation not found.")

        return self._build_api_response(conversation)

    async def get_all_conversations(
        self,
        prospect_id: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[dict]:
        """
        Retrieve conversation metadata with pagination.
        """

        if skip < 0:
            raise ValueError("Skip cannot be negative.")

        if not 1 <= limit <= 100:
            raise ValueError(
                "Limit must be between 1 and 100."
            )

        return await self.repository.get_all_conversations(
            prospect_id=prospect_id,
            skip=skip,
            limit=limit,
        )


conversation_service = ConversationService()
