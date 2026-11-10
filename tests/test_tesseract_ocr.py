
import io
import logging
import sys
from pathlib import Path

import cv2
import httpx
import numpy as np
import pytesseract

from PIL import Image, ImageOps
from pytesseract import Output

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


class AdvancedTesseractOCR:

    def load_image(self, source: str) -> np.ndarray:
        """Load image from local path or URL."""

        if source.startswith(("http://", "https://")):
            response = httpx.get(
                source,
                timeout=30,
                follow_redirects=True,
            )
            response.raise_for_status()
            image_bytes = response.content
        else:
            path = Path(source)

            if not path.is_file():
                raise FileNotFoundError(f"Image not found: {path}")

            image_bytes = path.read_bytes()

        with Image.open(io.BytesIO(image_bytes)) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            return np.array(image)

    def enhance_image(self, image: np.ndarray) -> np.ndarray:
        """Improve readability while preserving text details."""

        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

        height, width = gray.shape

        # Upscale small screenshots.
        if width < 1800:
            scale = 1800 / width
            gray = cv2.resize(
                gray,
                None,
                fx=scale,
                fy=scale,
                interpolation=cv2.INTER_CUBIC,
            )

        # Improve local contrast.
        clahe = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(8, 8),
        )
        enhanced = clahe.apply(gray)

        # Remove image noise.
        denoised = cv2.fastNlMeansDenoising(
            enhanced,
            None,
            h=10,
            templateWindowSize=7,
            searchWindowSize=21,
        )

        # Sharpen text.
        blurred = cv2.GaussianBlur(
            denoised,
            (0, 0),
            1.0,
        )

        sharpened = cv2.addWeighted(
            denoised,
            1.5,
            blurred,
            -0.5,
            0,
        )

        return sharpened

    def detect_text_regions(
        self,
        image: np.ndarray,
    ) -> list[tuple[int, int, int, int]]:
        """Detect candidate text regions using morphological operations."""

        _, binary = cv2.threshold(
            image,
            0,
            255,
            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
        )

        horizontal_kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (35, 3),
        )

        connected = cv2.morphologyEx(
            binary,
            cv2.MORPH_CLOSE,
            horizontal_kernel,
        )

        contours, _ = cv2.findContours(
            connected,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        height, width = image.shape
        regions = []

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)

            # Filter very small and very large regions.
            if w < width * 0.08:
                continue

            if h < 12 or h > height * 0.35:
                continue

            if w * h < 300:
                continue

            # Add padding around detected text.
            padding_x = 15
            padding_y = 10

            x1 = max(0, x - padding_x)
            y1 = max(0, y - padding_y)
            x2 = min(width, x + w + padding_x)
            y2 = min(height, y + h + padding_y)

            regions.append((x1, y1, x2, y2))

        regions.sort(key=lambda region: (region[1], region[0]))

        return self.merge_regions(regions)

    @staticmethod
    def merge_regions(
        regions: list[tuple[int, int, int, int]],
    ) -> list[tuple[int, int, int, int]]:
        """Merge overlapping or vertically adjacent regions."""

        if not regions:
            return []

        merged = []

        for current in regions:
            if not merged:
                merged.append(list(current))
                continue

            previous = merged[-1]

            horizontal_overlap = (
                current[0] <= previous[2]
                and current[2] >= previous[0]
            )

            vertical_gap = current[1] - previous[3]

            if horizontal_overlap and vertical_gap <= 35:
                previous[0] = min(previous[0], current[0])
                previous[1] = min(previous[1], current[1])
                previous[2] = max(previous[2], current[2])
                previous[3] = max(previous[3], current[3])
            else:
                merged.append(list(current))

        return [tuple(region) for region in merged]

    @staticmethod
    def run_ocr(
        image: np.ndarray,
        psm: int,
    ) -> tuple[str, float]:
        """Extract text and calculate word confidence."""

        config = f"--oem 3 --psm {psm}"

        data = pytesseract.image_to_data(
            image,
            lang="eng",
            config=config,
            output_type=Output.DICT,
        )

        words = []
        confidences = []

        for text, confidence in zip(
            data["text"],
            data["conf"],
        ):
            text = text.strip()

            try:
                confidence = float(confidence)
            except (ValueError, TypeError):
                continue

            if text and confidence >= 0:
                words.append(text)
                confidences.append(confidence)

        extracted_text = pytesseract.image_to_string(
            image,
            lang="eng",
            config=config,
        ).strip()

        average_confidence = (
            sum(confidences) / len(confidences)
            if confidences
            else 0.0
        )

        return extracted_text, average_confidence

    def extract(self, source: str) -> str:
        """Run advanced OCR with global and regional extraction."""

        original = self.load_image(source)
        enhanced = self.enhance_image(original)

        candidates = []

        # Global OCR configurations.
        for psm in (11, 6, 3):
            text, confidence = self.run_ocr(enhanced, psm)

            candidates.append({
                "method": f"global_psm_{psm}",
                "text": text,
                "confidence": confidence,
            })

        # Experimental region-based OCR.
        regions = self.detect_text_regions(enhanced)

        logger.info("Detected %s candidate text regions.", len(regions))

        region_results = []

        for index, (x1, y1, x2, y2) in enumerate(regions, start=1):
            crop = enhanced[y1:y2, x1:x2]

            if crop.size == 0:
                continue

            text, confidence = self.run_ocr(crop, 6)

            if text:
                region_results.append({
                    "region": index,
                    "text": text,
                    "confidence": confidence,
                })

        regional_text = "\n\n".join(
            item["text"] for item in region_results
        )

        regional_confidence = (
            sum(item["confidence"] for item in region_results)
            / len(region_results)
            if region_results
            else 0.0
        )

        if regional_text:
            candidates.append({
                "method": "regional_ocr",
                "text": regional_text,
                "confidence": regional_confidence,
            })

        # Rank candidates. Confidence is only a heuristic.
        candidates.sort(
            key=lambda item: item["confidence"],
            reverse=True,
        )

        print("\n========== OCR RESULTS ==========\n")

        for index, result in enumerate(candidates, start=1):
            print(
                f"Rank {index}: {result['method']} | "
                f"Confidence: {result['confidence']:.2f}%"
            )

        best = candidates[0]

        print("\n========== BEST OCR OUTPUT ==========\n")
        print(best["text"])

        return best["text"]


if __name__ == "__main__":

    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python tests/test_tesseract_ocr.py <image_path_or_url>"
        )

    try:
        ocr = AdvancedTesseractOCR()
        ocr.extract(sys.argv[1])

    except Exception:
        logger.exception("Advanced Tesseract OCR failed.")
        raise
