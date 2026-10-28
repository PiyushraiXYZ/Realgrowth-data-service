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

    async def enrich_people(
        self,
        person_ids: list[str],
        reveal_personal_emails: bool = False,
        reveal_phone_number: bool = False,
    ) -> dict:
        # 1. Get enriched data from Apollo
        response = await self.client.bulk_enrich_people(
            person_ids=person_ids,
            reveal_personal_emails=reveal_personal_emails,
            reveal_phone_number=reveal_phone_number,
        )

        # 2. Normalize Apollo response
        enriched_result = self.normalize_enriched_people(response)

        # 3. Save normalized data into MongoDB
        save_result = await self.save_enriched_people(enriched_result)

        # 4. Return enrichment + DB result
        return {
            "provider": "apollo",
            "total_requested": enriched_result.get("total_requested", 0),
            "unique_enriched": enriched_result.get("unique_enriched", 0),
            "missing_records": enriched_result.get("missing_records", 0),
            "created": save_result.get("created", 0),
            "updated": save_result.get("updated", 0),
            "skipped": save_result.get("skipped", 0),
            "saved": save_result.get("saved", []),
        }


    def normalize_enriched_people(
        self,
        response: dict,
    ) -> dict:

        matches = response.get("matches", [])

        prospects = []

        for person in matches:

            organization = person.get("organization") or {}

            prospects.append(
                {
                    "apollo_id": person.get("id"),

                    "first_name": person.get("first_name"),
                    "last_name": person.get("last_name"),
                    "name": person.get("name"),
                    "job_title": person.get("title"),

                    "email": person.get("email"),
                    "email_status": person.get(
                        "email_status"
                    ),

                    "linkedin_url": person.get(
                        "linkedin_url"
                    ),

                    # IMPORTANT:
                    # phone is from person, not organization
                    "phone": person.get("phone"),

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

                    "location": {
                        "city": person.get("city"),
                        "state": person.get("state"),
                        "country": person.get("country"),
                    },

                    "seniority": person.get(
                        "seniority"
                    ),

                    "departments": person.get(
                        "departments",
                        []
                    ),

                    "functions": person.get(
                        "functions",
                        []
                    ),

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

    async def save_enriched_people(
        self,
        enriched_result: dict,
    ) -> dict:

        prospects = enriched_result.get(
            "prospects",
            []
        )

        created = 0
        updated = 0
        skipped = 0

        saved = []

        for person in prospects:

            apollo_id = person.get("apollo_id")

            if not apollo_id:
                skipped += 1

                logger.warning(
                    "Skipping Apollo person without ID"
                )

                continue

            # Convert normalized Apollo data
            # into RealGrowth prospect schema.
            prospect = apollo_to_prospect(person)

            # Insert or update MongoDB.
            result = await self.repository.upsert_prospect(
                prospect
            )

            if result["action"] == "created":
                created += 1

            elif result["action"] == "updated":
                updated += 1



            saved.append(
    {
        "apollo_id": apollo_id,
        "name": person.get("name"),
        "first_name": person.get("first_name"),
        "last_name": person.get("last_name"),
        "title": person.get("job_title"),
        "email": person.get("email"),
        "email_status": person.get("email_status"),
        "linkedin_url": person.get("linkedin_url"),
        "phone": person.get("phone"),
        "company": (
            person.get("company") or {}
        ).get("name"),
        "company_website": (
            person.get("company") or {}
        ).get("website"),
        "company_linkedin_url": (
            person.get("company") or {}
        ).get("linkedin_url"),
        "location": person.get("location"),
        "seniority": person.get("seniority"),
        "action": result["action"],
        "prospect_id": result["id"],
    }
)    

                



        return {
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "saved": saved,
        }

    async def enrich_and_save_people(
        self,
        person_ids: list[str],
        reveal_personal_emails: bool = False,
        reveal_phone_number: bool = False,
    ) -> dict:

        # Step 1: Enrich people from Apollo
        enriched_result = await self.enrich_people(
            person_ids=person_ids,
            reveal_personal_emails=reveal_personal_emails,
            reveal_phone_number=reveal_phone_number,
        )

        # Step 2: Save enriched data into MongoDB
        save_result = await self.save_enriched_people(
            enriched_result
        )

        # Step 3: Return combined result
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