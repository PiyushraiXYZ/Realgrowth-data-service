from datetime import datetime, timezone

from app.connection_tracking.repository import ConnectionRepository
from app.connection_tracking.schemas import (
    CreateConnectionRequest,
    UpdateConnectionStatusRequest,
)
from app.connection_tracking.enums import ConnectionStatus
from app.connection_tracking.models import build_connection_document


class ConnectionService:

    def __init__(self):
        self.repository = ConnectionRepository()

    async def create_connection(
        self,
        request: CreateConnectionRequest,
    ) -> dict:

        existing = await self.repository.get_connection_by_prospect(
            prospect_id=request.prospect_id,
            platform=request.platform.value,
        )

        if existing:
            raise ValueError(
                "Connection already exists for this prospect and platform"
            )

        document = build_connection_document(request)

        return await self.repository.create_connection(document)

    async def get_connection(self, connection_id: str) -> dict:

        connection = await self.repository.get_connection_by_id(
            connection_id
        )

        if not connection:
            raise ValueError("Connection not found")

        return connection

    async def get_prospect_connections(
        self,
        prospect_id: str,
    ) -> list[dict]:

        return await self.repository.get_connections_by_prospect(
            prospect_id
        )

    async def update_connection_status(
        self,
        connection_id: str,
        request: UpdateConnectionStatusRequest,
    ) -> dict:

        connection = await self.repository.get_connection_by_id(
            connection_id
        )

        if not connection:
            raise ValueError("Connection not found")

        # Prevent duplicate events
        if request.event_id in connection.get("processed_event_ids", []):
            raise ValueError("Event already processed")

        current_status = connection["current_status"]
        new_status = request.status.value

        # Allowed status transitions
        allowed_transitions = {
            ConnectionStatus.INITIATED.value: [
                ConnectionStatus.SENT.value,
                ConnectionStatus.FAILED.value,
            ],
            ConnectionStatus.SENT.value: [
                ConnectionStatus.PENDING.value,
                ConnectionStatus.ACCEPTED.value,
                ConnectionStatus.REJECTED.value,
                ConnectionStatus.WITHDRAWN.value,
            ],
            ConnectionStatus.PENDING.value: [
                ConnectionStatus.ACCEPTED.value,
                ConnectionStatus.REJECTED.value,
                ConnectionStatus.WITHDRAWN.value,
            ],
            ConnectionStatus.FAILED.value: [
                ConnectionStatus.INITIATED.value,
            ],
        }

        if new_status not in allowed_transitions.get(current_status, []):
            raise ValueError(
                f"Invalid status transition: {current_status} -> {new_status}"
            )

        updated_connection = await self.repository.update_connection_status(
            connection_id=connection_id,
            status=new_status,
            event_id=request.event_id,
            source=request.source.value,
            notes=request.notes,
            occurred_at=request.occurred_at or datetime.now(timezone.utc),
        )

        if not updated_connection:
            raise ValueError("Unable to update connection status")

        return updated_connection