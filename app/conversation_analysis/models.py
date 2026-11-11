
from datetime import datetime, timezone
from uuid import uuid4


def get_current_timestamp() -> datetime:
    return datetime.now(timezone.utc)


def build_conversation_document(
    prospect_id: str,
    screenshots: list[dict],
) -> dict:
    now = get_current_timestamp()

    return {
        "conversation_id": str(uuid4()),
        "prospect_id": prospect_id,
        "screenshots": screenshots,

        # Internal OCR and layout data
        "extracted_messages": [],

        # Structured conversation for LLM
        "reconstructed_conversation": None,

        # Future LLM result
        "analysis": None,

        "status": "UPLOADED",
        "analysis_status": "PENDING",

        "created_at": now,
        "updated_at": now,
    }
