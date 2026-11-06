from datetime import datetime, timezone
from uuid import uuid4

from app.connection_tracking.schemas import CreateConnectionRequest


def get_current_timestamp() -> datetime:
    return datetime.now(timezone.utc)


def build_history_entry(
    event_id: str,
    status: str,
    source: str,
    timestamp: datetime | None = None,
    notes: str | None = None,
) -> dict:
    return {
        "event_id": event_id,
        "status": status,
        "source": source,
        "timestamp": timestamp or get_current_timestamp(),
        "notes": notes,
    }


def build_connection_document(
    request: CreateConnectionRequest,
) -> dict:
    now = get_current_timestamp()

    history_entry = build_history_entry(
        event_id=request.event_id,
        status=request.status.value,
        source=request.source.value,
        timestamp=now,
    )

    return {
        "connection_id": str(uuid4()),
        "prospect_id": request.prospect_id,
        "platform": request.platform.value,
        "current_status": request.status.value,
        "history": [history_entry],
        "processed_event_ids": [request.event_id],
        "created_at": now,
        "updated_at": now,
    }