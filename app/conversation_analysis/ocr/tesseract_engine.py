
import asyncio
import io
import logging
import os
from urllib.parse import urlparse

import cv2
import httpx
import numpy as np
import pytesseract
from PIL import Image, ImageOps
from pytesseract import Output

logger = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 15 * 1024 * 1024
ALLOWED_HOST_SUFFIXES = ("res.cloudinary.com",)


class TesseractOCREngine:
    def __init__(self):
        # Windows path can be configured through TESSERACT_CMD.
        tesseract_cmd = os.getenv("TESSERACT_CMD")

        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

        self.language = os.getenv("TESSERACT_LANGUAGE", "eng")
        self.psm = int(os.getenv("TESSERACT_PSM", "11"))
        self.oem = int(os.getenv("TESSERACT_OEM", "3"))
        self.target_width = 1800

    @staticmethod
    def _validate_image_url(image_url: str) -> None:
        parsed = urlparse(image_url)

        if parsed.scheme != "https":
            raise ValueError("Only HTTPS image URLs are allowed.")

        hostname = (parsed.hostname or "").lower()

        if not any(
            hostname == suffix or hostname.endswith(f".{suffix}")
            for suffix in ALLOWED_HOST_SUFFIXES
        ):
            raise ValueError("Image URL host is not allowed.")

    async def _download_image(self, image_url: str) -> bytes:
        self._validate_image_url(image_url)

        timeout = httpx.Timeout(20.0, connect=5.0)

        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,
        ) as client:
            async with client.stream("GET", image_url) as response:
                response.raise_for_status()

                content_type = response.headers.get(
                    "content-type", ""
                ).lower()

                if not content_type.startswith("image/"):
                    raise ValueError("Cloudinary URL did not return an image.")

                content_length = response.headers.get("content-length")

                if content_length and int(content_length) > MAX_IMAGE_BYTES:
                    raise ValueError("Image exceeds the 15 MB limit.")

                image_bytes = bytearray()

                async for chunk in response.aiter_bytes():
                    image_bytes.extend(chunk)

                    if len(image_bytes) > MAX_IMAGE_BYTES:
                        raise ValueError("Image exceeds the 15 MB limit.")

        return bytes(image_bytes)

    def _preprocess(self, image_bytes: bytes):
        with Image.open(io.BytesIO(image_bytes)) as source:
            source = ImageOps.exif_transpose(source)
            source.load()

            if source.width < 100 or source.height < 100:
                raise ValueError("Image resolution is too small for OCR.")

            image = source.convert("RGB")

        image_array = np.array(image)
        gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)

        # Upscale small screenshots to improve character recognition.
        if gray.shape[1] < self.target_width:
            scale = self.target_width / gray.shape[1]
            new_height = int(gray.shape[0] * scale)

            gray = cv2.resize(
                gray,
                (self.target_width, new_height),
                interpolation=cv2.INTER_CUBIC,
            )

        # Improve local contrast without aggressive thresholding.
        clahe = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(8, 8),
        )
        enhanced = clahe.apply(gray)

        return enhanced

    def _run_tesseract(self, image_array: np.ndarray) -> dict:
        config = f"--oem {self.oem} --psm {self.psm}"

        data = pytesseract.image_to_data(
            image_array,
            lang=self.language,
            config=config,
            output_type=Output.DICT,
        )

        words = []
        text_lines = []
        confidences = []

        current_line_key = None
        current_line_words = []

        for index, raw_text in enumerate(data["text"]):
            word = raw_text.strip()

            try:
                confidence = float(data["conf"][index])
            except (TypeError, ValueError):
                confidence = -1.0

            if not word or confidence < 0:
                continue

            x = int(data["left"][index])
            y = int(data["top"][index])
            width = int(data["width"][index])
            height = int(data["height"][index])

            line_key = (
                int(data["page_num"][index]),
                int(data["block_num"][index]),
                int(data["par_num"][index]),
                int(data["line_num"][index]),
            )

            if current_line_key is not None and line_key != current_line_key:
                if current_line_words:
                    text_lines.append(" ".join(current_line_words))
                current_line_words = []

            current_line_key = line_key
            current_line_words.append(word)
            confidences.append(confidence)

            words.append({
                "text": word,
                "confidence": round(confidence, 2),
                "bbox": {
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                },
                "line_id": {
                    "page": line_key[0],
                    "block": line_key[1],
                    "paragraph": line_key[2],
                    "line": line_key[3],
                },
            })

        if current_line_words:
            text_lines.append(" ".join(current_line_words))

        average_confidence = (
            sum(confidences) / len(confidences)
            if confidences else 0.0
        )

        return {
            "text": "\n".join(text_lines).strip(),
            "words": words,
            "average_confidence": round(average_confidence, 2),
            "word_count": len(words),
            "image_width": int(image_array.shape[1]),
            "image_height": int(image_array.shape[0]),
            "engine": "tesseract",
            "language": self.language,
            "psm": self.psm,
        }

    async def extract(self, image_url: str) -> dict:
        image_bytes = await self._download_image(image_url)

        result = await asyncio.to_thread(
            self._extract_sync,
            image_bytes,
        )

        logger.info(
            "Tesseract OCR completed: words=%s confidence=%.2f",
            result["word_count"],
            result["average_confidence"],
        )

        return result

    def _extract_sync(self, image_bytes: bytes) -> dict:
        processed_image = self._preprocess(image_bytes)
        return self._run_tesseract(processed_image)


tesseract_ocr_engine = TesseractOCREngine()
