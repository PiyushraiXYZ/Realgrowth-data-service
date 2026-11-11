
import asyncio
import logging
import sys
from pathlib import Path

from app.conversation_analysis.ocr.tesseract_engine import (
    tesseract_ocr_engine,
)
from app.conversation_analysis.ocr.layout_analyzer import (
    layout_analyzer,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def run_pipeline(image_paths: list[str]):
    all_results = []

    logger.info("Processing %s screenshots", len(image_paths))

    for index, image_path in enumerate(image_paths, start=1):
        path = Path(image_path)

        if not path.exists():
            logger.error("Image not found: %s", path)
            continue

        logger.info(
            "Processing screenshot %s: %s",
            index,
            path.name,
        )

        image_bytes = path.read_bytes()

        # 1. Tesseract OCR
        ocr_result = await asyncio.to_thread(
            tesseract_ocr_engine._extract_sync,
            image_bytes,
        )

        # 2. Layout analysis
        layout_result = layout_analyzer.analyze(
            ocr_result=ocr_result,
            screenshot_index=index,
        )

        result = {
            "screenshot_index": index,
            "filename": path.name,
            "extracted_text": ocr_result.get("text", ""),
            "ocr": ocr_result,
            "layout": layout_result,
        }

        all_results.append(result)

        logger.info(
            "Screenshot %s completed | Words: %s | "
            "Confidence: %s | Lines: %s | Blocks: %s",
            index,
            ocr_result.get("word_count"),
            ocr_result.get("average_confidence"),
            layout_result["line_count"],
            layout_result["block_count"],
        )

    # 3. Combined report
    total_words = sum(
        item["ocr"].get("word_count", 0)
        for item in all_results
    )

    total_lines = sum(
        item["layout"]["line_count"]
        for item in all_results
    )

    total_blocks = sum(
        item["layout"]["block_count"]
        for item in all_results
    )

    print("\n" + "=" * 65)
    print("MULTI-SCREENSHOT OCR REPORT")
    print("=" * 65)

    for result in all_results:
        print(f"\nScreenshot: {result['filename']}")
        print(f"Words: {result['ocr']['word_count']}")
        print(f"Confidence: {result['ocr']['average_confidence']}")
        print(f"Lines: {result['layout']['line_count']}")
        print(f"Blocks: {result['layout']['block_count']}")

        print("\nExtracted text:")
        print(result["extracted_text"])

        print("\nDetected blocks:")

        for block in result["layout"]["blocks"]:
            print(
                f"\n{block['block_id']} | "
                f"Words: {block['word_count']}"
            )
            print(block["text"])

    print("\n" + "=" * 65)
    print("FINAL SUMMARY")
    print("=" * 65)
    print(f"Screenshots processed: {len(all_results)}")
    print(f"Total words: {total_words}")
    print(f"Total lines: {total_lines}")
    print(f"Total blocks: {total_blocks}")

    if len(all_results) != len(image_paths):
        logger.warning(
            "Some screenshots could not be processed."
        )

    return all_results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(
            "Usage: python -m tests.test_tesseract_pipeline "
            "<image1> <image2> ..."
        )

    asyncio.run(run_pipeline(sys.argv[1:]))
