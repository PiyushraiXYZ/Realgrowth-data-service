import asyncio
import logging
from datetime import datetime, timezone

from app.celery_app import celery_app
from app.config.settings import settings
from app.database.mongodb import (
    connect_to_mongodb,
    close_mongodb_connection,
)
from app.conversation_analysis.repository import ConversationRepository
from app.conversation_analysis.ocr.tesseract_engine import (
    tesseract_ocr_engine,
)
from app.conversation_analysis.ocr.layout_analyzer import (
    layout_analyzer,
)
from app.conversation_analysis.conversation_reconstructor import (
    conversation_reconstructor,
)
from app.conversation_analysis.image_processor import GroqOCRService
from app.conversation_analysis.llm_service import ConversationLLMService

logger = logging.getLogger(__name__)


async def _process_conversation(conversation_id: str) -> dict:
    repository = ConversationRepository()

    groq_ocr_service = None
    llm_service = None

    try:
        # Each Celery worker process owns its MongoDB connection.
        await connect_to_mongodb()

        conversation = await repository.get_conversation(
            conversation_id
        )

        if not conversation:
            raise ValueError(
                f"Conversation not found: {conversation_id}"
            )

        screenshots = conversation.get("screenshots", [])

        if not screenshots:
            raise ValueError(
                f"No screenshots found: {conversation_id}"
            )

        reconstructed = conversation.get(
            "reconstructed_conversation"
        )

        # Create Groq clients inside this worker's event loop.
        groq_ocr_service = GroqOCRService()
        llm_service = ConversationLLMService()

        # -------------------------------------------------
        # STEP 1: OCR + Layout + Reconstruction
        # Skip this stage if reconstruction was already saved.
        # -------------------------------------------------
        if not reconstructed:
            await repository.update_ocr_status(
                conversation_id,
                "OCR_PROCESSING",
            )

            extracted_messages = []

            for index, screenshot in enumerate(
                screenshots,
                start=1,
            ):
                image_url = screenshot.get("image_url")

                if not image_url:
                    raise ValueError(
                        f"Screenshot {index} has no image URL."
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
                    or ocr_result.get(
                        "average_confidence", 0
                    ) < 55
                )

                if (
                    low_quality
                    and groq_ocr_service.client
                ):
                    try:
                        groq_text = (
                            await groq_ocr_service.extract_text(
                                image_url=image_url
                            )
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
                            "Groq OCR fallback failed | "
                            "conversation_id=%s | screenshot=%s",
                            conversation_id,
                            index,
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

            reconstructed = conversation_reconstructor.reconstruct(
                extracted_messages
            )

            saved = await repository.update_ocr_results(
                conversation_id=conversation_id,
                extracted_messages=extracted_messages,
                reconstructed_conversation=reconstructed,
            )

            if not saved:
                raise RuntimeError(
                    "Failed to save OCR and reconstruction results."
                )

            logger.info(
                "Reconstruction completed | conversation_id=%s",
                conversation_id,
            )

        else:
            logger.info(
                "Using previously saved reconstruction | "
                "conversation_id=%s",
                conversation_id,
            )

        # -------------------------------------------------
        # STEP 2: LLM Analysis
        # -------------------------------------------------
        await repository.update_analysis_status(
            conversation_id,
            "PROCESSING",
        )

        try:
            analysis_result = (
                await llm_service.analyze_conversation(
                    reconstructed
                )
            )

            if not isinstance(analysis_result, dict):
                raise ValueError(
                    "LLM returned an invalid analysis result."
                )

            saved = await repository.update_analysis_result(
                conversation_id=conversation_id,
                analysis_result=analysis_result,
            )

            if not saved:
                raise RuntimeError(
                    "Failed to save LLM analysis result."
                )

        except Exception:
            await repository.update_analysis_status(
                conversation_id,
                "FAILED",
            )

            logger.exception(
                "LLM analysis failed | conversation_id=%s",
                conversation_id,
            )
            raise

        logger.info(
            "Conversation processing completed | conversation_id=%s",
            conversation_id,
        )

        return {
            "conversation_id": conversation_id,
            "status": "COMPLETED",
            "analysis_status": "COMPLETED",
        }

    except Exception:
        logger.exception(
            "Conversation processing failed | conversation_id=%s",
            conversation_id,
        )
        raise

    finally:
        # Close Groq clients created in this event loop.
        if groq_ocr_service and groq_ocr_service.client:
            await groq_ocr_service.close()

        if llm_service and llm_service.client:
            await llm_service.client.close()

        await close_mongodb_connection()


@celery_app.task(
    bind=True,
    name="app.conversation_analysis.tasks.process_conversation_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def process_conversation_task(
    self,
    conversation_id: str,
) -> dict:
    """
    Celery entry point.

    Runs the async conversation pipeline in the worker's event loop.
    """

    logger.info(
        "Celery task started | conversation_id=%s | task_id=%s | retry=%s",
        conversation_id,
        self.request.id,
        self.request.retries,
    )

    return asyncio.run(
        _process_conversation(conversation_id)
    )
