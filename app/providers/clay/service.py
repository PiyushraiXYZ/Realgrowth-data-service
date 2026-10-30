import logging

from app.providers.clay.client import ClayClient
from app.repositories.prospect_repository import ProspectRepository
from app.services.prospect_mapper import clay_to_prospect


logger = logging.getLogger(__name__)


class ClayService:

    def __init__(self):
        self.client = ClayClient()
        self.repository = ProspectRepository()

    async def get_search_fields(self) -> dict:
        """
        Get the valid Clay people-search fields.
        """

        return await self.client.get_search_fields(
            source_type="people"
        )

    @staticmethod
    def _map_seniority(seniority: str) -> str:
        """
        Convert RealGrowth seniority values into
        Clay's actual allowed seniority values.
        """

        seniority_mapping = {
            "c_suite": "c-suite",
            "c-suite": "c-suite",
            "board_member": "board-member",
            "board-member": "board-member",
            "mid_level": "mid-level",
            "mid-level": "mid-level",
            "vp": "vp",
            "founder": "founder",
            "owner": "owner",
            "partner": "partner",
            "director": "director",
            "head": "head",
            "manager": "manager",
            "senior": "senior",
            "entry": "entry",
            "intern": "intern",
            "unknown": "unknown",
        }

        return seniority_mapping.get(
            seniority,
            seniority,
        )

    async def search_people(
        self,
        target: str | None = None,
        country: str | None = None,
        decision_maker: str | None = None,
        industry: str | None = None,
        seniority: str | None = None,
        filters: dict | None = None,
        page: int = 1,
        per_page: int = 10,
    ) -> dict:
        """
        Search people using Clay and save the results
        into the RealGrowth prospects collection.

        ProspectRepository also publishes the scoring job
        to RabbitMQ after a successful MongoDB save.
        """

        filters = dict(filters or {})

        if target:
            filters["company_description_keywords"] = [
                target.strip()
            ]

        if country:
            filters["location_countries_include"] = [
                country.strip()
            ]

        if decision_maker:
            filters["job_title_keywords"] = [
                decision_maker.strip()
            ]

        if industry:
            filters["company_industries_include"] = [
                industry.strip()
            ]

        if seniority:
            filters["job_title_seniority_levels_v2"] = [
                self._map_seniority(seniority)
            ]

        search_payload = {
            "source_type": "people",
            "filters": filters,
        }

        # -----------------------------------------------------
        # Step 1: Create Clay search
        # -----------------------------------------------------

        search_response = await self.client.create_people_search(
            search_payload
        )

        search_id = search_response.get("search_id")

        if not search_id:
            search_id = search_response.get("id")

        if not search_id:
            raise RuntimeError(
                f"Clay did not return search_id: "
                f"{search_response}"
            )

        # -----------------------------------------------------
        # Step 2: Run Clay search
        # -----------------------------------------------------

        run_payload = {
            "page": page,
            "per_page": per_page,
        }

        response = await self.client.run_people_search(
            search_id=search_id,
            payload=run_payload,
        )

        # -----------------------------------------------------
        # Step 3: Extract people
        # -----------------------------------------------------

        people = response.get(
            "people",
            response.get(
                "results",
                response.get(
                    "data",
                    [],
                ),
            ),
        )

        if people is None:
            people = []

        # -----------------------------------------------------
        # Step 4: Total
        # -----------------------------------------------------

        total = response.get(
            "total",
            response.get(
                "total_count",
                response.get(
                    "total_results",
                    len(people),
                ),
            ),
        )

        # -----------------------------------------------------
        # Step 5: Save Clay people into MongoDB
        # -----------------------------------------------------

        created = 0
        updated = 0
        skipped = 0
        saved = []

        for person in people:

            try:
                prospect = clay_to_prospect(
                    person
                )

                if not prospect:
                    skipped += 1
                    continue

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
                    skipped += 1

                saved.append(
                    {
                        "provider_id": prospect.get(
                            "providerId"
                        ),

                        "name": prospect.get(
                            "name"
                        ),

                        "title": prospect.get(
                            "title"
                        ),

                        "company": prospect.get(
                            "company"
                        ),

                        "website": prospect.get(
                            "website"
                        ),

                        "industry": prospect.get(
                            "industry"
                        ),

                        "location": prospect.get(
                            "location"
                        ),

                        "action": action,

                        "prospect_id": result.get(
                            "id"
                        ),
                    }
                )

                logger.info(
                    "Clay prospect saved | action=%s | prospect_id=%s",
                    action,
                    result.get("id"),
                )

            except Exception as exc:
                skipped += 1

                logger.exception(
                    "Failed to save Clay prospect | provider_id=%s",
                    person.get("id"),
                )

                saved.append(
                    {
                        "provider_id": person.get(
                            "id"
                        ),

                        "name": person.get(
                            "name"
                        ),

                        "action": "skipped",

                        "error": str(exc),
                    }
                )

        # IMPORTANT:
        # Do NOT call ProspectScoringService here.
        # RabbitMQ scoring is triggered by ProspectRepository.

        return {
            "provider": "clay",
            "search_id": search_id,
            "total": total,
            "created": created,
            "updated": updated,
            "saved": saved,
            "people": people,
            "pagination": {
                "page": page,
                "per_page": per_page,
            },
            "filters": filters,
        }