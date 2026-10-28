from app.providers.clay.client import ClayClient


class ClayService:
    def __init__(self):
        self.client = ClayClient()

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
        page: int = 1,
        per_page: int = 10,
    ) -> dict:
        """
        Search people using Clay.

        RealGrowth -> Clay mapping:

        target
            -> company_description_keywords

        country
            -> location_countries_include

        decision_maker
            -> job_title_keywords

        industry
            -> company_industries_include

        seniority
            -> job_title_seniority_levels_v2
        """

        filters: dict = {}


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


        run_payload = {
            "page": page,
            "per_page": per_page,
        }

        response = await self.client.run_people_search(
            search_id=search_id,
            payload=run_payload,
        )


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


        return {
            "provider": "clay",
            "search_id": search_id,
            "total": total,
            "people": people,
            "pagination": {
                "page": page,
                "per_page": per_page,
            },
            "filters": filters,
        }