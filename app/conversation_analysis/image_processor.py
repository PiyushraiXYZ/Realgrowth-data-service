
import logging
from groq import AsyncGroq

from app.config.settings import settings

logger = logging.getLogger(__name__)


class GroqOCRService:
    def __init__(self):
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is not configured.")

        self.client = AsyncGroq(api_key=settings.groq_api_key)
        self.model = settings.groq_ocr_model

    async def extract_text(self, image_url: str) -> str:
        """
        Extract visible text from one conversation screenshot.
        Does not infer missing senders or timestamps.
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an OCR engine. Extract text exactly as "
                            "visible in the supplied screenshot. Preserve "
                            "message order, sender labels, timestamps, "
                            "line breaks and visible UI labels. Do not "
                            "summarize, infer, correct, or invent text. "
                            "Mark unreadable text as [unclear]. If the "
                            "image is not a conversation, extract the "
                            "visible text without pretending it is one."
                        ),
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url},
                            },
                            {
                                "type": "text",
                                "text": (
                                    "Extract all readable text from this "
                                    "image. Preserve the original wording "
                                    "and reading order."
                                ),
                            },
                        ],
                    },
                ],
                max_completion_tokens=2048,
                temperature=0,
            )

            extracted_text = response.choices[0].message.content

            if not extracted_text or not extracted_text.strip():
                raise ValueError("OCR returned empty text.")

            return extracted_text.strip()

        except Exception:
            logger.exception("Groq OCR failed for screenshot.")
            raise

    async def close(self):
        await self.client.close()


groq_ocr_service = GroqOCRService()
