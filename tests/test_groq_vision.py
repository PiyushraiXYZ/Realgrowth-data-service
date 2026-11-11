
import asyncio
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from groq import AsyncGroq
from app.config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_vision_model(image_url: str) -> None:
    client = AsyncGroq(api_key=settings.groq_api_key)

    try:
        response = await client.chat.completions.create(
            model=settings.groq_ocr_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Extract all visible text from this conversation "
                                "screenshot. Preserve sender labels, timestamps, "
                                "message order and original wording. "
                                "Do not invent unclear information. "
                                "Return only the extracted conversation."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                    ],
                }
            ],
            max_completion_tokens=2048,
        )

        extracted_text = response.choices[0].message.content

        logger.info("OCR extraction completed successfully.")
        print("\nExtracted conversation:\n")
        print(extracted_text)

    finally:
        await client.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python tests/test_groq_vision.py <image_url>"
        )

    asyncio.run(test_vision_model(sys.argv[1]))
