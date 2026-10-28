import logging
from datetime import datetime, timezone

from app.config.settings import settings
from app.database.mongodb import get_database

logger = logging.getLogger(__name__)


class ProspectRepository:

    @property
    def collection(self):
        db = get_database()
        return db[settings.mongodb_prospect_collection]

    # ---------------------------------------------------------
    # FIND BY PROVIDER ID
    # ---------------------------------------------------------

    async def find_by_provider_id(
        self,
        provider: str,
        provider_id: str,
    ):
        if not provider or not provider_id:
            return None

        return await self.collection.find_one(
            {
                "provider": provider,
                "providerId": provider_id,
            }
        )

    # ---------------------------------------------------------
    # FIND BY EMAIL
    # ---------------------------------------------------------

    async def find_by_email(
        self,
        email: str,
    ):
        if not email:
            return None

        normalized_email = email.strip().lower()

        if not normalized_email:
            return None

        return await self.collection.find_one(
            {
                "email": normalized_email,
            }
        )

    # ---------------------------------------------------------
    # FIND BY LINKEDIN
    # ---------------------------------------------------------

    async def find_by_linkedin(
        self,
        linkedin_url: str,
    ):
        if not linkedin_url:
            return None

        normalized_url = self._normalize_linkedin_url(
            linkedin_url
        )

        if not normalized_url:
            return None

        return await self.collection.find_one(
            {
                "linkedinUrl": normalized_url,
            }
        )

    # ---------------------------------------------------------
    # NORMALIZE LINKEDIN URL
    # ---------------------------------------------------------

    @staticmethod
    def _normalize_linkedin_url(
        linkedin_url: str,
    ) -> str:

        if not linkedin_url:
            return ""

        url = linkedin_url.strip().lower()

        # Remove protocol
        url = url.replace(
            "https://",
            "",
        )

        url = url.replace(
            "http://",
            "",
        )

        # Remove www.
        if url.startswith("www."):
            url = url[4:]

        # Remove trailing slash
        url = url.rstrip("/")

        return f"https://{url}"

    # ---------------------------------------------------------
    # NORMALIZE EMAIL
    # ---------------------------------------------------------

    @staticmethod
    def _normalize_email(
        email: str | None,
    ) -> str:

        if not email:
            return ""

        return email.strip().lower()

    # ---------------------------------------------------------
    # UPSERT PROSPECT
    # ---------------------------------------------------------

    async def upsert_prospect(
        self,
        prospect: dict,
    ) -> dict:

        if not prospect:
            raise ValueError(
                "Prospect data cannot be empty."
            )

        provider = prospect.get(
            "provider"
        )

        provider_id = prospect.get(
            "providerId"
        )

        email = self._normalize_email(
            prospect.get("email")
        )

        linkedin_url = self._normalize_linkedin_url(
            prospect.get("linkedinUrl")
        )

        # Keep normalized values in the prospect
        if email:
            prospect["email"] = email

        if linkedin_url:
            prospect["linkedinUrl"] = linkedin_url

        existing = None

        # -----------------------------------------------------
        # 1. SAME PROVIDER + PROVIDER ID
        # -----------------------------------------------------

        if provider and provider_id:

            existing = await self.find_by_provider_id(
                provider=provider,
                provider_id=provider_id,
            )

        # -----------------------------------------------------
        # 2. SAME LINKEDIN PROFILE
        # -----------------------------------------------------

        if not existing and linkedin_url:

            existing = await self.find_by_linkedin(
                linkedin_url
            )

        # -----------------------------------------------------
        # 3. SAME EMAIL
        # -----------------------------------------------------

        if not existing and email:

            existing = await self.find_by_email(
                email
            )

        now = datetime.now(timezone.utc)

        # =====================================================
        # EXISTING PROSPECT
        # =====================================================

        if existing:

            existing_id = existing["_id"]

            updates = {}

            # Fields that should never be overwritten
            # during an update.
            protected_fields = {
                "_id",
                "createdAt",
            }

            for key, value in prospect.items():

                if key in protected_fields:
                    continue

                # Don't overwrite useful existing data
                # with empty values.
                if value in (
                    None,
                    "",
                    [],
                    {},
                ):
                    continue

                updates[key] = value

            updates["updatedAt"] = now

            await self.collection.update_one(
                {
                    "_id": existing_id,
                },
                {
                    "$set": updates,
                },
            )

            logger.info(
                "Prospect updated | provider=%s | provider_id=%s",
                provider,
                provider_id,
            )

            return {
                "action": "updated",
                "id": str(existing_id),
            }

        # =====================================================
        # NEW PROSPECT
        # =====================================================

        prospect["createdAt"] = now
        prospect["updatedAt"] = now

        result = await self.collection.insert_one(
            prospect
        )

        logger.info(
            "Prospect created | provider=%s | provider_id=%s",
            provider,
            provider_id,
        )

        return {
            "action": "created",
            "id": str(result.inserted_id),
        }

    # ---------------------------------------------------------
    # COUNT
    # ---------------------------------------------------------

    async def count(self) -> int:
        return await self.collection.count_documents({})