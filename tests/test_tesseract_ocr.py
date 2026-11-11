import asyncio
import logging
import sys

from pathlib import Path

from app.conversation_analysis.ocr.tesseract_engine import (
    tesseract_ocr_engine,
)

logging.basicConfig(level=logging.INFO)


async def main():
    image_path = Path(sys.argv[1])

    image_bytes = image_path.read_bytes()

    result = await asyncio.to_thread(
        tesseract_ocr_engine._extract_sync,
        image_bytes,
    )

    print("\n--- OCR TEXT ---")
    print(result["text"])

    print("\n--- OCR METRICS ---")
    print("Words:", result["word_count"])
    print("Confidence:", result["average_confidence"])
    print("Image width:", result["image_width"])
    print("Image height:", result["image_height"])

    print("\n--- FIRST 10 WORDS ---")
    for word in result["words"][:10]:
        print(word)


if __name__ == "__main__":
    asyncio.run(main())