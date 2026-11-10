
import sys
from pathlib import Path

# Add project root to Python import path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


import asyncio
import logging
import sys

from huggingface_hub import InferenceClient
from app.config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_vision_model(image_url: str) -> None:
    if not settings.huggingface_api_token:
        raise ValueError("Hugging Face API token is missing.")

    client = InferenceClient(
        provider=settings.huggingface_provider,
        api_key=settings.huggingface_api_token,
    )

    response = client.chat.completions.create(
        model=settings.huggingface_ocr_model,
        messages=[
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
                            "Extract all visible text from this conversation "
                            "screenshot. Preserve the original wording, "
                            "sender labels and timestamps when visible. "
                            "Do not guess missing or unclear information. "
                            "Return only the extracted conversation text."
                        ),
                    },
                ],
            }
        ],
        max_tokens=1500,
    )

    extracted_text = response.choices[0].message.content

    logger.info("Vision model response received.")
    print("\nExtracted conversation:\n")
    print(extracted_text)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(
            "Usage: python scripts/test_hf_vision.py <image_url>"
        )

    asyncio.run(test_vision_model(sys.argv[1]))
