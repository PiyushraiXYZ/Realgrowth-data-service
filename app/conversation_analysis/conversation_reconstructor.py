
import logging
import re
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class ConversationReconstructor:
    """
    Convert OCR and layout output into a normalized conversation
    suitable for downstream LLM analysis.

    Sender identity is never inferred from ordinary message text.
    """

    TIME_PATTERN = re.compile(
        r"^\s*(?:\[)?"
        r"(?P<time>(?:[01]?\d|2[0-3]):[0-5]\d"
        r"(?:\s?[APap][Mm])?)"
        r"(?:\])?\s*(?:[✓✔☑]+|[0-9]+)?\s*$"
    )

    DATE_PATTERN = re.compile(
        r"^\s*(?:"
        r"\d{1,2}\s+[A-Za-z]+\s+\d{4}|"
        r"[A-Za-z]+\s+\d{1,2},?\s+\d{4}|"
        r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
        r")\s*$",
        re.IGNORECASE,
    )

    EMAIL_PATTERN = re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    )

    EMAIL_HEADERS = {
        "from": re.compile(r"^\s*from\s*:\s*(.+)$", re.I),
        "to": re.compile(r"^\s*to\s*:\s*(.+)$", re.I),
        "cc": re.compile(r"^\s*cc\s*:\s*(.+)$", re.I),
        "subject": re.compile(r"^\s*subject\s*:\s*(.+)$", re.I),
        "date": re.compile(r"^\s*date\s*:\s*(.+)$", re.I),
    }

    UI_NOISE_PATTERNS = [
        re.compile(r"^\s*(?:online|typing\.\.\.)\s*$", re.I),
        re.compile(r"^\s*(?:message|type a message|write a message)\s*$", re.I),
        re.compile(r"^\s*(?:©|®|™)?\s*[)\]]?\s*message\s*$", re.I),
        re.compile(r"^\s*\d{1,3}%\s*$"),
        re.compile(r"^\s*(?:wifi|wi-fi|battery|bluetooth)\s*$", re.I),
        re.compile(r"^\s*[•·|\\/_\-_=+~`]{1,5}\s*$"),
    ]

    def reconstruct(
        self,
        screenshot_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not screenshot_results:
            return self._empty_result()

        screenshots = sorted(
            screenshot_results,
            key=lambda item: item.get("screenshot_index", 0),
        )

        blocks: list[dict[str, Any]] = []
        combined_text: list[str] = []
        screenshot_widths: dict[int, int] = {}

        for screenshot in screenshots:
            screenshot_index = screenshot.get("screenshot_index", 0)
            ocr = screenshot.get("ocr") or {}
            layout = screenshot.get("layout") or {}

            screenshot_text = (
                screenshot.get("extracted_text")
                or ocr.get("text")
                or ""
            )

            if screenshot_text:
                combined_text.append(screenshot_text)

            screenshot_widths[screenshot_index] = (
                ocr.get("image_width") or 0
            )

            for block_index, block in enumerate(layout.get("blocks") or []):
                text = self._get_block_text(block)

                if not text:
                    continue

                blocks.append({
                    "screenshot_index": screenshot_index,
                    "block_index": block_index,
                    "text": text,
                    "bbox": block.get("bbox") or {},
                    "confidence": block.get("average_confidence"),
                })

            # Fallback only when layout blocks are unavailable.
            if not layout.get("blocks") and screenshot_text:
                for line_index, line in enumerate(screenshot_text.splitlines()):
                    if line.strip():
                        blocks.append({
                            "screenshot_index": screenshot_index,
                            "block_index": line_index,
                            "text": line.strip(),
                            "bbox": {},
                            "confidence": None,
                        })

        full_text = "\n".join(combined_text)
        source_type = self._detect_source_type(full_text)
        metadata = self._extract_metadata(full_text, source_type)

        messages = self._build_messages(
            blocks=blocks,
            screenshot_widths=screenshot_widths,
        )

        for index, message in enumerate(messages, start=1):
            message["sequence"] = index

        participants = self._extract_participants(metadata, messages)

        return {
            "source_type": source_type,
            "subject": metadata.get("subject"),
            "participants": participants,
            "messages": messages,
        }

    @staticmethod
    def _get_block_text(block: dict) -> str:
        text = block.get("text")

        if text and str(text).strip():
            return str(text).strip()

        lines = block.get("lines") or []
        return "\n".join(
            str(line.get("text", "")).strip()
            for line in lines
            if line.get("text")
        ).strip()

    def _detect_source_type(self, text: str) -> str:
        lowered = text.lower()

        email_headers = sum(
            1
            for header in ("from:", "to:", "subject:", "date:", "cc:")
            if header in lowered
        )

        if email_headers >= 2:
            return "email"

        if any(term in lowered for term in (
            "inbox", "sent mail", "reply", "forward"
        )) and "@" in text:
            return "email"

        if text.strip():
            return "messaging_or_chat"

        return "unknown"

    def _extract_metadata(
        self,
        text: str,
        source_type: str,
    ) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "emails": sorted(set(self.EMAIL_PATTERN.findall(text))),
        }

        for field, pattern in self.EMAIL_HEADERS.items():
            match = pattern.search(text)

            if match:
                metadata[field] = match.group(1).strip()

        if source_type == "email":
            metadata["document_type"] = "email"

        return metadata

    def _build_messages(
        self,
        blocks: list[dict],
        screenshot_widths: dict[int, int],
    ) -> list[dict[str, Any]]:
        messages = []
        current_date = None

        ordered_blocks = sorted(
            blocks,
            key=lambda item: (
                item["screenshot_index"],
                (item.get("bbox") or {}).get("y", 0),
                (item.get("bbox") or {}).get("x", 0),
            ),
        )

        for block in ordered_blocks:
            raw_text = block["text"]
            lines = [
                line.strip()
                for line in raw_text.splitlines()
                if line.strip()
            ]

            if not lines:
                continue

            content_lines = []
            timestamp = None

            for line in lines:
                if self.DATE_PATTERN.match(line):
                    current_date = line
                    continue

                time_match = self.TIME_PATTERN.match(line)
                if time_match:
                    if timestamp is None:
                        timestamp = self._normalize_timestamp(
                            time_match.group("time")
                        )
                    continue

                if self._is_noise(line):
                    continue

                if self._is_email_header(line):
                    continue

                content_lines.append(line)

            content = self._clean_text("\n".join(content_lines))

            if not self._is_valid_message(content):
                continue

            bbox = block.get("bbox") or {}
            screenshot_index = block["screenshot_index"]
            image_width = screenshot_widths.get(screenshot_index, 0)

            side_hint = self._get_side_hint(
                bbox=bbox,
                image_width=image_width,
            )

            confidence = block.get("confidence")

            messages.append({
                "sender": None,
                "timestamp": timestamp,
                "date": current_date,
                "text": content,
                "side_hint": side_hint,
                "confidence": self._confidence_label(confidence),
            })

        return messages

    def _is_noise(self, text: str) -> bool:
        normalized = text.strip()

        if not normalized:
            return True

        if self.TIME_PATTERN.match(normalized):
            return True

        if self.DATE_PATTERN.match(normalized):
            return True

        if any(pattern.match(normalized) for pattern in self.UI_NOISE_PATTERNS):
            return True

        # Reject isolated OCR fragments and common status-bar artifacts.
        if len(normalized) <= 2:
            return True

        if re.fullmatch(r"[\W_]+", normalized):
            return True

        return False

    def _is_email_header(self, text: str) -> bool:
        return any(
            pattern.match(text)
            for pattern in self.EMAIL_HEADERS.values()
        )

    @staticmethod
    def _clean_text(text: str) -> str:
        lines = [
            re.sub(r"\s+", " ", line).strip()
            for line in text.splitlines()
        ]
        return "\n".join(line for line in lines if line).strip()

    @staticmethod
    def _is_valid_message(text: str) -> bool:
        if not text:
            return False

        # A short but meaningful reply such as "Yes." or "No." is valid.
        if len(text) >= 3 and re.search(r"[A-Za-z0-9]", text):
            return True

        return False

    @staticmethod
    def _normalize_timestamp(value: str) -> str:
        cleaned = re.sub(r"\s+", " ", value).strip().upper()

        try:
            parsed = datetime.strptime(cleaned, "%I:%M %p")
            return parsed.strftime("%I:%M %p")
        except ValueError:
            pass

        try:
            parsed = datetime.strptime(cleaned, "%H:%M")
            return parsed.strftime("%H:%M")
        except ValueError:
            return cleaned

    @staticmethod
    def _get_side_hint(
        bbox: dict,
        image_width: int,
    ) -> str | None:
        if not bbox or not image_width:
            return None

        x = bbox.get("x")
        width = bbox.get("width")

        if x is None or width is None:
            return None

        center_x = x + (width / 2)
        midpoint = image_width / 2

        if center_x < midpoint * 0.9:
            return "left"

        if center_x > midpoint * 1.1:
            return "right"

        return None

    @staticmethod
    def _confidence_label(value: Any) -> str:
        if value is None:
            return "unknown"

        try:
            score = float(value)
        except (TypeError, ValueError):
            return "unknown"

        if score >= 85:
            return "high"

        if score >= 65:
            return "medium"

        return "low"

    @staticmethod
    def _extract_participants(
        metadata: dict,
        messages: list[dict],
    ) -> list[dict]:
        participants = []

        for field in ("from", "to", "cc"):
            value = metadata.get(field)

            if value:
                participants.append({
                    "name": value,
                    "role": field,
                })

        # Do not derive participant names from message sentences.
        return participants

    @staticmethod
    def _empty_result() -> dict:
        return {
            "source_type": "unknown",
            "subject": None,
            "participants": [],
            "messages": [],
        }


conversation_reconstructor = ConversationReconstructor()
