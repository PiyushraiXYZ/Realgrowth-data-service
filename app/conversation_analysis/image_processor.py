
import logging

from groq import AsyncGroq

from app.config.settings import settings

logger = logging.getLogger(__name__)


class GroqOCRService:
    def __init__(self):
        self.client = (
            AsyncGroq(api_key=settings.groq_api_key)
            if settings.groq_api_key
            else None
        )
        self.model = settings.groq_ocr_model

    async def extract_text(self, image_url: str) -> str:
        if not self.client:
            raise RuntimeError("GROQ_API_KEY is not configured.")

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an OCR engine. Extract only text "
                            "visible in the supplied image. Preserve "
                            "original wording and reading order. Do not "
                            "summarize, infer, correct, or invent text. "
                            "Mark unreadable text as [unclear]."
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
                                    "Extract all readable text. Preserve "
                                    "the original wording and order."
                                ),
                            },
                        ],
                    },
                ],
                max_completion_tokens=2048,
            )

            content = response.choices[0].message.content

            if not content or not content.strip():
                raise ValueError("Groq OCR returned empty text.")

            return content.strip()

        except Exception:
            logger.exception("Groq fallback OCR failed.")
            raise

    async def close(self):
        if self.client:
            await self.client.close()


groq_ocr_service = GroqOCRService()
