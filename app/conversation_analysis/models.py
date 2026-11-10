
from datetime import datetime, timezone
from uuid import uuid4


def get_current_timestamp() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


def build_conversation_document(
    prospect_id: str,
    screenshots: list[dict],
) -> dict:
    """Build MongoDB document for a new conversation."""

    now = get_current_timestamp()

    return {
        "conversation_id": str(uuid4()),
        "prospect_id": prospect_id,

        # Uploaded screenshot details
        "screenshots": screenshots,

        # Extracted conversation data (populated later by OCR)
        "extracted_messages": [],

        # AI analysis results (populated later by LLM)
        "analysis": None,

        # Processing status
        "status": "UPLOADED",
        "analysis_status": "PENDING",

        "created_at": now,
        "updated_at": now,
    }
