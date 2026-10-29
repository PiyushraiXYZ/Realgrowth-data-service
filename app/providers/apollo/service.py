import logging

from app.providers.apollo.client import ApolloClient
from app.repositories.prospect_repository import ProspectRepository
from app.services.prospect_mapper import apollo_to_prospect


logger = logging.getLogger(__name__)


class ApolloService:

    def __init__(self):
        self.client = ApolloClient()
        self.repository = ProspectRepository()

    async def search_people(self, payload: dict) -> dict:
        response = await self.client.search_people(payload)

        return {
            "provider": "apollo",
            "total": response.get("total_entries", 0),
            "people": response.get("people", []),
            "pagination": {
                "page": payload.get("page", 1),
                "per_page": payload.get("per_page", 10),
            },
        }

    # =========================================================
    # ENRICH PEOPLE
    # =========================================================

    async def enrich_people(
        self,
        person_ids: list[str],
        reveal_personal_emails: bool = False,
        reveal_phone_number: bool = False,
    ) -> dict:

        if not person_ids:
            raise ValueError(
                "At least one Apollo person ID is required."
            )

        if len(person_ids) > 10:
            raise ValueError(
                "Apollo allows a maximum of 10 people per bulk enrichment request."
            )

        logger.info(
            "Starting Apollo enrichment | person_count=%s",
            len(person_ids),
        )

        # -----------------------------------------------------
        # 1. Get enriched data from Apollo
        # -----------------------------------------------------

        response = await self.client.bulk_enrich_people(
            person_ids=person_ids,
            reveal_personal_emails=reveal_personal_emails,
            reveal_phone_number=reveal_phone_number,
        )

        logger.info(
            "Apollo enrichment response | requested=%s | enriched=%s | missing=%s",
            response.get(
                "total_requested_enrichments",
                0,
            ),
            response.get(
                "unique_enriched_records",
                0,
            ),
            response.get(
                "missing_records",
                0,
            ),
        )

        # -----------------------------------------------------
        # 2. Normalize Apollo response
        # -----------------------------------------------------

        enriched_result = self.normalize_enriched_people(
            response
        )

        prospects = enriched_result.get(
            "prospects",
            [],
        )

        logger.info(
            "Apollo normalization completed | valid_prospects=%s",
            len(prospects),
        )

        # -----------------------------------------------------
        # 3. Save normalized data into MongoDB
        # -----------------------------------------------------

        save_result = await self.save_enriched_people(
            enriched_result
        )

        logger.info(
            "Apollo MongoDB save completed | created=%s | updated=%s | skipped=%s",
            save_result.get("created", 0),
            save_result.get("updated", 0),
            save_result.get("skipped", 0),
        )

        # -----------------------------------------------------
        # 4. Return final response
        # -----------------------------------------------------

        return {
            "provider": "apollo",

            "total_requested": enriched_result.get(
                "total_requested",
                0,
            ),

            "unique_enriched": enriched_result.get(
                "unique_enriched",
                0,
            ),

            "missing_records": enriched_result.get(
                "missing_records",
                0,
            ),

            "created": save_result.get(
                "created",
                0,
            ),

            "updated": save_result.get(
                "updated",
                0,
            ),

            "skipped": save_result.get(
                "skipped",
                0,
            ),

            "saved": save_result.get(
                "saved",
                [],
            ),
        }

    # =========================================================
    # NORMALIZE APOLLO RESPONSE
    # =========================================================

    def normalize_enriched_people(
        self,
        response: dict,
    ) -> dict:

        matches = response.get("matches") or []

        prospects = []

        for person in matches:

            # Apollo can return null for unmatched records.
            if not person:
                logger.warning(
                    "Apollo returned an unmatched/null person."
                )
                continue

            apollo_id = person.get("id")

            if not apollo_id:
                logger.warning(
                    "Skipping Apollo person without ID."
                )
                continue

            organization = (
                person.get("organization")
                or {}
            )

            prospects.append(
                {
                    # -----------------------------------------
                    # Person
                    # -----------------------------------------

                    "apollo_id": apollo_id,

                    "first_name": person.get(
                        "first_name"
                    ),

                    "last_name": person.get(
                        "last_name"
                    ),

                    "name": person.get(
                        "name"
                    ),

                    "job_title": person.get(
                        "title"
                    ),

                    "email": person.get(
                        "email"
                    ),

                    "email_status": person.get(
                        "email_status"
                    ),

                    "linkedin_url": person.get(
                        "linkedin_url"
                    ),

                    "phone": person.get(
                        "phone"
                    ),

                    # -----------------------------------------
                    # Company
                    # -----------------------------------------

                    "company": {
                        "id": person.get(
                            "organization_id"
                        ),

                        "name": organization.get(
                            "name"
                        ),

                        "website": organization.get(
                            "primary_domain"
                        ),

                        "linkedin_url": organization.get(
                            "linkedin_url"
                        ),

                        "industry": organization.get(
                            "industry"
                        ),

                        "employee_count": organization.get(
                            "estimated_num_employees"
                        ),

                        "city": organization.get(
                            "city"
                        ),

                        "state": organization.get(
                            "state"
                        ),

                        "country": organization.get(
                            "country"
                        ),
                    },

                    # -----------------------------------------
                    # Location
                    # -----------------------------------------

                    "location": {
                        "city": person.get(
                            "city"
                        ),

                        "state": person.get(
                            "state"
                        ),

                        "country": person.get(
                            "country"
                        ),
                    },

                    # -----------------------------------------
                    # Job information
                    # -----------------------------------------

                    "seniority": person.get(
                        "seniority"
                    ),

                    "departments": person.get(
                        "departments",
                        [],
                    ),

                    "functions": person.get(
                        "functions",
                        [],
                    ),

                    # -----------------------------------------
                    # Apollo metadata
                    # -----------------------------------------

                    "match_confidence": person.get(
                        "match_confidence"
                    ),

                    "photo_url": person.get(
                        "photo_url"
                    ),
                }
            )

        return {
            "provider": "apollo",

            "total_requested": response.get(
                "total_requested_enrichments",
                0,
            ),

            "unique_enriched": response.get(
                "unique_enriched_records",
                0,
            ),

            "missing_records": response.get(
                "missing_records",
                0,
            ),

            "prospects": prospects,
        }

    # =========================================================
    # SAVE ENRICHED PEOPLE
    # =========================================================

    async def save_enriched_people(
        self,
        enriched_result: dict,
    ) -> dict:

        prospects = (
            enriched_result.get("prospects")
            or []
        )

        created = 0
        updated = 0
        skipped = 0

        saved = []

        for person in prospects:

            apollo_id = person.get(
                "apollo_id"
            )

            # ---------------------------------------------
            # Validate Apollo ID
            # ---------------------------------------------

            if not apollo_id:

                skipped += 1

                logger.warning(
                    "Skipping Apollo person without ID."
                )

                continue

            # ---------------------------------------------
            # Convert Apollo data into RealGrowth schema
            # ---------------------------------------------

            prospect = apollo_to_prospect(
                person
            )

            logger.info(
                "Saving Apollo prospect | provider=%s | providerId=%s | name=%s",
                prospect.get("provider"),
                prospect.get("providerId"),
                prospect.get("name"),
            )

            # ---------------------------------------------
            # Save / update MongoDB
            # ---------------------------------------------

            result = await self.repository.upsert_prospect(
                prospect
            )

            action = result.get(
                "action"
            )

            if action == "created":
                created += 1

            elif action == "updated":
                updated += 1

            else:
                logger.warning(
                    "Unknown MongoDB action: %s",
                    action,
                )

            # ---------------------------------------------
            # Response data
            # ---------------------------------------------

            company = (
                person.get("company")
                or {}
            )

            saved.append(
                {
                    "apollo_id": apollo_id,

                    "name": person.get(
                        "name"
                    ),

                    "first_name": person.get(
                        "first_name"
                    ),

                    "last_name": person.get(
                        "last_name"
                    ),

                    "title": person.get(
                        "job_title"
                    ),

                    "email": person.get(
                        "email"
                    ),

                    "email_status": person.get(
                        "email_status"
                    ),

                    "linkedin_url": person.get(
                        "linkedin_url"
                    ),

                    "phone": person.get(
                        "phone"
                    ),

                    "company": company.get(
                        "name"
                    ),

                    "company_website": company.get(
                        "website"
                    ),

                    "company_linkedin_url": company.get(
                        "linkedin_url"
                    ),

                    "location": person.get(
                        "location"
                    ),

                    "seniority": person.get(
                        "seniority"
                    ),

                    "match_confidence": person.get(
                        "match_confidence"
                    ),

                    "action": action,

                    "prospect_id": result.get(
                        "id"
                    ),
                }
            )

            logger.info(
                "Apollo prospect saved | providerId=%s | action=%s | mongo_id=%s",
                apollo_id,
                action,
                result.get("id"),
            )

        return {
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "saved": saved,
        }