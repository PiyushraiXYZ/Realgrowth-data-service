
import logging
from collections import defaultdict
from statistics import median
from typing import Any

logger = logging.getLogger(__name__)


class LayoutAnalyzer:

    def analyze(
        self,
        ocr_result: dict[str, Any],
        screenshot_index: int = 0,
    ) -> dict[str, Any]:

        words = ocr_result.get("words", [])

        if not words:
            logger.warning(
                "No OCR words found for screenshot %s",
                screenshot_index,
            )
            return self._empty_result(screenshot_index)

        lines = self._build_lines(words)
        blocks = self._build_blocks(lines)

        logger.info(
            "Layout analysis completed for screenshot %s: "
            "%s lines, %s blocks",
            screenshot_index,
            len(lines),
            len(blocks),
        )

        return {
            "screenshot_index": screenshot_index,
            "lines": lines,
            "blocks": blocks,
            "line_count": len(lines),
            "block_count": len(blocks),
        }

    def _build_lines(
        self,
        words: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:

        grouped_words = defaultdict(list)

        for word in words:
            text = str(word.get("text", "")).strip()

            if not text:
                continue

            # FIX: Read coordinates from nested bbox.
            bbox = word.get("bbox", {})

            x = bbox.get("x", 0)
            y = bbox.get("y", 0)
            width = bbox.get("width", 0)
            height = bbox.get("height", 0)

            if width <= 0 or height <= 0:
                continue

            line_id = word.get("line_id")

            if isinstance(line_id, dict):
                line_key = (
                    line_id.get("page"),
                    line_id.get("block"),
                    line_id.get("paragraph"),
                    line_id.get("line"),
                )
            else:
                line_key = line_id

            if line_key is None:
                line_key = (
                    "geometry",
                    round(y / max(height, 1)),
                )

            grouped_words[line_key].append({
                "text": text,
                "confidence": float(
                    word.get("confidence", -1)
                ),
                "x": x,
                "y": y,
                "width": width,
                "height": height,
            })

        lines = []

        for line_key, line_words in grouped_words.items():
            line_words.sort(key=lambda item: item["x"])

            left = min(word["x"] for word in line_words)
            top = min(word["y"] for word in line_words)

            right = max(
                word["x"] + word["width"]
                for word in line_words
            )

            bottom = max(
                word["y"] + word["height"]
                for word in line_words
            )

            valid_confidences = [
                word["confidence"]
                for word in line_words
                if word["confidence"] >= 0
            ]

            avg_confidence = (
                sum(valid_confidences) / len(valid_confidences)
                if valid_confidences
                else 0.0
            )

            lines.append({
                "line_id": str(line_key),
                "text": " ".join(
                    word["text"] for word in line_words
                ),
                "bbox": {
                    "x": left,
                    "y": top,
                    "width": right - left,
                    "height": bottom - top,
                },
                "average_confidence": round(
                    avg_confidence, 2
                ),
                "word_count": len(line_words),
                "words": line_words,
            })

        return sorted(
            lines,
            key=lambda line: (
                line["bbox"]["y"],
                line["bbox"]["x"],
            ),
        )

    def _build_blocks(
        self,
        lines: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:

        if not lines:
            return []

        typical_height = median(
            line["bbox"]["height"] for line in lines
        )

        typical_height = max(typical_height, 1)

        blocks = []
        current_lines = [lines[0]]

        for next_line in lines[1:]:
            previous_line = current_lines[-1]

            if self._should_merge(
                previous_line,
                next_line,
                typical_height,
            ):
                current_lines.append(next_line)
            else:
                blocks.append(
                    self._create_block(
                        current_lines,
                        len(blocks),
                    )
                )

                current_lines = [next_line]

        if current_lines:
            blocks.append(
                self._create_block(
                    current_lines,
                    len(blocks),
                )
            )

        return blocks

    def _should_merge(
        self,
        previous: dict[str, Any],
        current: dict[str, Any],
        typical_height: float,
    ) -> bool:

        previous_bbox = previous["bbox"]
        current_bbox = current["bbox"]

        previous_bottom = (
            previous_bbox["y"] + previous_bbox["height"]
        )

        vertical_gap = current_bbox["y"] - previous_bottom

        if vertical_gap > typical_height * 1.8:
            return False

        if vertical_gap < -typical_height:
            return False

        previous_left = previous_bbox["x"]
        current_left = current_bbox["x"]

        previous_right = previous_left + previous_bbox["width"]
        current_right = current_left + current_bbox["width"]

        horizontal_overlap = (
            min(previous_right, current_right)
            - max(previous_left, current_left)
        )

        has_overlap = horizontal_overlap > 0

        has_similar_alignment = (
            abs(previous_left - current_left)
            <= typical_height * 2.5
        )

        return has_overlap or has_similar_alignment

    def _create_block(
        self,
        lines: list[dict[str, Any]],
        block_index: int,
    ) -> dict[str, Any]:

        left = min(
            line["bbox"]["x"] for line in lines
        )

        top = min(
            line["bbox"]["y"] for line in lines
        )

        right = max(
            line["bbox"]["x"] + line["bbox"]["width"]
            for line in lines
        )

        bottom = max(
            line["bbox"]["y"] + line["bbox"]["height"]
            for line in lines
        )

        total_words = sum(
            line["word_count"] for line in lines
        )

        confidence_values = [
            line["average_confidence"]
            for line in lines
            if line["average_confidence"] > 0
        ]

        average_confidence = (
            sum(confidence_values) / len(confidence_values)
            if confidence_values
            else 0.0
        )

        return {
            "block_id": f"block_{block_index}",
            "text": "\n".join(
                line["text"] for line in lines
            ),
            "bbox": {
                "x": left,
                "y": top,
                "width": right - left,
                "height": bottom - top,
            },
            "line_ids": [
                line["line_id"] for line in lines
            ],
            "line_count": len(lines),
            "word_count": total_words,
            "average_confidence": round(
                average_confidence, 2
            ),
            "source": "tesseract",
        }

    @staticmethod
    def _empty_result(screenshot_index: int) -> dict[str, Any]:
        return {
            "screenshot_index": screenshot_index,
            "lines": [],
            "blocks": [],
            "line_count": 0,
            "block_count": 0,
        }


layout_analyzer = LayoutAnalyzer()
