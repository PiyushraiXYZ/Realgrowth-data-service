from app.providers.apollo.client import ApolloClient


class ApolloService:

    def __init__(self):
        self.client = ApolloClient()

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

        response = await self.client.bulk_enrich_people(
            person_ids=person_ids,
            reveal_personal_emails=reveal_personal_emails,
            reveal_phone_number=reveal_phone_number,
        )

        return self.normalize_enriched_people(response)

    def normalize_enriched_people(
        self,
        response: dict,
    ) -> dict:

        matches = response.get("matches", [])

        prospects = []

        for person in matches:
            organization = person.get(
                "organization"
            ) or {}

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

                    "phone": organization.get(
                        "phone"
                    ),

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