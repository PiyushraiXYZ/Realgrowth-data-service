
import logging
from datetime import datetime, timezone

from app.connection_tracking.repository import ConnectionRepository
from app.connection_tracking.schemas import (
    CreateConnectionRequest,
    UpdateConnectionStatusRequest,
)
from app.connection_tracking.enums import ConnectionStatus
from app.connection_tracking.models import build_connection_document


logger = logging.getLogger(__name__)


class ConnectionService:

    # ---------------------------------------------------------
    # Allowed Connection Status Transitions
    # ---------------------------------------------------------

    ALLOWED_TRANSITIONS = {
        ConnectionStatus.INITIATED.value: {
            ConnectionStatus.SENT.value,
            ConnectionStatus.FAILED.value,
        },

        ConnectionStatus.SENT.value: {
            ConnectionStatus.PENDING.value,
            ConnectionStatus.ACCEPTED.value,
            ConnectionStatus.REJECTED.value,
            ConnectionStatus.WITHDRAWN.value,
            ConnectionStatus.FAILED.value,
        },

        ConnectionStatus.PENDING.value: {
            ConnectionStatus.ACCEPTED.value,
            ConnectionStatus.REJECTED.value,
            ConnectionStatus.WITHDRAWN.value,
            ConnectionStatus.FAILED.value,
        },

        # Terminal statuses
        ConnectionStatus.ACCEPTED.value: set(),
        ConnectionStatus.REJECTED.value: set(),
        ConnectionStatus.WITHDRAWN.value: set(),

        # Failed connections can be retried.
        ConnectionStatus.FAILED.value: {
            ConnectionStatus.INITIATED.value,
        },
    }

    def __init__(self):
        self.repository = ConnectionRepository()

    # ---------------------------------------------------------
    # Create Connection
    # ---------------------------------------------------------

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

        connection = await self.repository.create_connection(document)

        logger.info(
            "Connection created | prospect_id=%s | platform=%s",
            request.prospect_id,
            request.platform.value,
        )

        return connection

    # ---------------------------------------------------------
    # Get Connection
    # ---------------------------------------------------------

    async def get_connection(
        self,
        connection_id: str,
    ) -> dict:

        connection = await self.repository.get_connection_by_id(
            connection_id
        )

        if not connection:
            raise ValueError("Connection not found")

        return connection

    # ---------------------------------------------------------
    # Get All Prospect Connections
    # ---------------------------------------------------------

    async def get_prospect_connections(
        self,
        prospect_id: str,
    ) -> list[dict]:

        return await self.repository.get_connections_by_prospect(
            prospect_id
        )

    # ---------------------------------------------------------
    # Validate Status Transition
    # ---------------------------------------------------------

    @classmethod
    def validate_status_transition(
        cls,
        current_status: str,
        new_status: str,
    ) -> None:

        allowed_statuses = cls.ALLOWED_TRANSITIONS.get(
            current_status,
            set(),
        )

        if new_status not in allowed_statuses:
            raise ValueError(
                f"Invalid status transition: "
                f"{current_status} -> {new_status}. "
                f"Allowed next statuses: "
                f"{', '.join(sorted(allowed_statuses)) or 'None'}"
            )

    # ---------------------------------------------------------
    # Update Connection Status
    # ---------------------------------------------------------

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

        # Prevent duplicate events.
        processed_event_ids = connection.get(
            "processed_event_ids",
            [],
        )

        if request.event_id in processed_event_ids:
            raise ValueError("Event already processed")

        current_status = connection.get("current_status")

        if not current_status:
            raise ValueError(
                "Connection does not have a valid current status"
            )

        new_status = request.status.value

        # Validate the requested status transition.
        self.validate_status_transition(
            current_status=current_status,
            new_status=new_status,
        )

        # Use the supplied event timestamp or current UTC time.
        occurred_at = (
            request.occurred_at
            or datetime.now(timezone.utc)
        )

        # Persist the status update and event information.
        updated_connection = (
            await self.repository.update_connection_status(
                connection_id=connection_id,
                status=new_status,
                event_id=request.event_id,
                source=request.source.value,
                notes=request.notes,
                occurred_at=occurred_at,
            )
        )

        if not updated_connection:
            raise ValueError(
                "Unable to update connection status"
            )

        logger.info(
            "Connection status updated | "
            "connection_id=%s | old_status=%s | new_status=%s | event_id=%s",
            connection_id,
            current_status,
            new_status,
            request.event_id,
        )

        return updated_connection
