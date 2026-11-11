
import logging
from datetime import datetime, timezone

from fastapi import UploadFile

from app.conversation_analysis.llm_service import (
    conversation_llm_service,
)
from app.conversation_analysis.ocr.tesseract_engine import (
    tesseract_ocr_engine,
)
from app.conversation_analysis.ocr.layout_analyzer import (
    layout_analyzer,
)
from app.conversation_analysis.conversation_reconstructor import (
    conversation_reconstructor,
)
from app.conversation_analysis.repository import ConversationRepository
from app.conversation_analysis.models import build_conversation_document
from app.conversation_analysis.image_processor import groq_ocr_service
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
        Upload screenshots, create a conversation, and process
        OCR, reconstruction, and LLM analysis.
        """

        if not prospect_id or not prospect_id.strip():
            raise ValueError("Prospect ID is required.")

        if not files:
            raise ValueError("Please upload at least one screenshot.")

        if len(files) > 10:
            raise ValueError("Maximum 10 screenshots allowed.")

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
            # STEP 1: Upload screenshots to Cloudinary.
            for file in files:
                image_data = await cloudinary_storage.upload_image(
                    file=file
                )

                uploaded_images.append({
                    **image_data,
                    "filename": file.filename,
                })

            # STEP 2: Create initial MongoDB document.
            document = build_conversation_document(
                prospect_id=prospect_id,
                screenshots=uploaded_images,
            )

            document["status"] = "OCR_PENDING"

            conversation = await self.repository.create_conversation(
                document
            )

            database_saved = True
            conversation_id = conversation["conversation_id"]

            logger.info(
                "Conversation created successfully: %s",
                conversation_id,
            )

            # STEP 3: Start OCR, reconstruction, and LLM analysis.
            try:
                return await self.process_conversation_ocr(
                    conversation_id=conversation_id
                )

            except Exception:
                logger.exception(
                    "OCR/reconstruction failed for conversation %s",
                    conversation_id,
                )

                await self.repository.update_ocr_status(
                    conversation_id=conversation_id,
                    status="OCR_FAILED",
                )

                failed_conversation = (
                    await self.repository.get_conversation(
                        conversation_id
                    )
                )

                if failed_conversation:
                    return self._build_api_response(
                        failed_conversation
                    )

                raise

        except Exception:
            logger.exception(
                "Screenshot upload failed for prospect %s",
                prospect_id,
            )

            # Clean up Cloudinary files only when the MongoDB
            # conversation document was not successfully created.
            if not database_saved:
                for image in uploaded_images:
                    public_id = image.get("public_id")

                    if not public_id:
                        continue

                    try:
                        await cloudinary_storage.delete_image(
                            public_id
                        )
                    except Exception:
                        logger.exception(
                            "Cloudinary cleanup failed for %s",
                            public_id,
                        )

            raise

    async def get_conversation(
        self,
        conversation_id: str,
    ) -> dict:
        """
        Get one conversation using the clean API response format.
        """

        conversation = await self.repository.get_conversation(
            conversation_id
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
        Get conversation metadata with pagination.
        """

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
        """
        Process screenshots through:
        1. Tesseract OCR
        2. Layout analysis
        3. Groq OCR fallback when Tesseract quality is low
        4. Conversation reconstruction
        5. Groq LLM conversation analysis
        """

        conversation = await self.repository.get_conversation(
            conversation_id
        )

        if not conversation:
            raise ValueError("Conversation not found.")

        screenshots = conversation.get("screenshots", [])

        if not screenshots:
            raise ValueError("No screenshots found.")

        extracted_messages = []

        # STEP 1: OCR and layout analysis.
        for index, screenshot in enumerate(screenshots, start=1):

            image_url = screenshot.get("image_url")

            if not image_url:
                raise ValueError(
                    f"Screenshot {index} does not contain an image URL."
                )

            ocr_result = await tesseract_ocr_engine.extract(
                image_url=image_url
            )

            layout_result = layout_analyzer.analyze(
                ocr_result=ocr_result,
                screenshot_index=index,
            )

            fallback_used = False
            fallback_error = None

            low_quality = (
                ocr_result.get("word_count", 0) == 0
                or ocr_result.get("average_confidence", 0) < 55
            )

            # STEP 2: Groq OCR fallback if Tesseract quality is low.
            if low_quality and groq_ocr_service.client:
                try:
                    groq_text = await groq_ocr_service.extract_text(
                        image_url=image_url
                    )

                    if groq_text:
                        ocr_result["tesseract_text"] = (
                            ocr_result.get("text", "")
                        )

                        ocr_result["text"] = groq_text
                        ocr_result["engine"] = "groq_fallback"

                        fallback_used = True

                except Exception as exc:
                    fallback_error = str(exc)

                    logger.warning(
                        "Groq OCR fallback failed for screenshot %s "
                        "in conversation %s",
                        index,
                        conversation_id,
                        exc_info=True,
                    )

            extracted_messages.append({
                "screenshot_index": index,
                "filename": screenshot.get("filename"),
                "public_id": screenshot.get("public_id"),
                "extracted_text": ocr_result.get("text", ""),
                "ocr": ocr_result,
                "layout": layout_result,
                "fallback_used": fallback_used,
                "fallback_error": fallback_error,
                "extracted_at": datetime.now(timezone.utc),
            })

        # STEP 3: Reconstruct the conversation.
        reconstructed_conversation = (
            conversation_reconstructor.reconstruct(
                extracted_messages
            )
        )

        # STEP 4: Save OCR and reconstruction results in MongoDB.
        updated_conversation = (
            await self.repository.update_ocr_results(
                conversation_id=conversation_id,
                extracted_messages=extracted_messages,
                reconstructed_conversation=reconstructed_conversation,
            )
        )

        if not updated_conversation:
            raise ValueError(
                "Failed to save OCR and reconstruction results."
            )

        logger.info(
            "Conversation reconstruction completed: %s",
            conversation_id,
        )

        # STEP 5: Run Groq LLM analysis.
        await self.process_conversation_analysis(
            conversation_id=conversation_id,
            reconstructed_conversation=reconstructed_conversation,
        )

        # STEP 6: Fetch the latest document because LLM analysis
        # may have updated the status and analysis result.
        final_conversation = await self.repository.get_conversation(
            conversation_id
        )

        if not final_conversation:
            raise ValueError(
                "Conversation not found after processing."
            )

        return self._build_api_response(final_conversation)

    async def process_conversation_analysis(
        self,
        conversation_id: str,
        reconstructed_conversation: dict,
    ) -> dict | None:
        """
        Send reconstructed conversation to Groq LLM,
        save the analysis result, and update its status.

        LLM failure does not invalidate successful OCR
        or conversation reconstruction.
        """

        await self.repository.update_analysis_status(
            conversation_id=conversation_id,
            status="PROCESSING",
        )

        try:
            logger.info(
                "Starting Groq LLM analysis for conversation %s",
                conversation_id,
            )

            analysis_result = (
                await conversation_llm_service.analyze_conversation(
                    conversation=reconstructed_conversation
                )
            )

            if not isinstance(analysis_result, dict):
                raise ValueError(
                    "Groq LLM returned an invalid analysis result."
                )

            saved = await self.repository.update_analysis_result(
                conversation_id=conversation_id,
                analysis_result=analysis_result,
            )

            if not saved:
                raise ValueError(
                    "Failed to save LLM analysis result."
                )

            logger.info(
                "Groq LLM analysis completed successfully: %s",
                conversation_id,
            )

            return analysis_result

        except Exception:
            logger.exception(
                "Groq LLM analysis failed for conversation %s",
                conversation_id,
            )

            await self.repository.update_analysis_status(
                conversation_id=conversation_id,
                status="FAILED",
            )

            return None


conversation_service = ConversationService()
