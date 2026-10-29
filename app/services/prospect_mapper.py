def build_base_prospect(
    *,
    name: str = "",
    title: str = "",
    location: str = "",
    company: str = "",
    website: str = "",
    industry: str = "",
    source: str,
    source_engine: str,
    search_title: str = "",
    search_snippet: str = "",
    search_url: str = "",
) -> dict:

    return {
        "name": name,
        "title": title,
        "location": location,
        "company": company,
        "website": website,
        "industry": industry,
        "companySize": "",
        "services": [],
        "priority": 0,
        "decisionScore": 0,
        "capabilities": [],
        "strengths": [],
        "gaps": [],
        "partnershipAngle": "",
        "partnershipScore": 0,
        "source": source,
        "sourceEngine": source_engine,
        "searchTitle": search_title,
        "searchSnippet": search_snippet,
        "searchUrl": search_url,
        "relationshipStage": "DISCOVERED",
        "relationshipScore": 0,
        "trustLevel": 0,
        "engagementScore": 0,
        "pipelineStage": "DISCOVERED",
        "stage": "NEW",
        "processing": {
            "intelligence": False,
            "readiness": False,
            "presence": False,
            "entryPlan": False,
            "relationship": False,
            "activity": False,
            "opportunity": False,
            "meeting": False,
        },
        "overallScore": 0,
        "archived": False,
        "active": True,
        "feedPostsCount": 0,
        "discoveredFromFeed": False,
        "feedPostIds": [],
    }


def apollo_to_prospect(person: dict) -> dict:

    company = person.get("company") or {}
    location = person.get("location") or {}

    prospect = build_base_prospect(
        name=person.get("name") or "",
        title=person.get("job_title") or "",
        location=(
            location.get("country")
            or company.get("country")
            or ""
        ),
        company=company.get("name") or "",
        website=company.get("website") or "",
        industry=company.get("industry") or "",
        source="APOLLO",
        source_engine="APOLLO",
        search_url=person.get("linkedin_url") or "",
    )

    # Provider identity
    prospect["provider"] = "apollo"
    prospect["providerId"] = person.get("apollo_id")

    # Person information
    prospect["firstName"] = person.get("first_name")
    prospect["lastName"] = person.get("last_name")

    prospect["email"] = person.get("email")
    prospect["emailStatus"] = person.get(
        "email_status"
    )

    prospect["linkedinUrl"] = person.get(
        "linkedin_url"
    )

    prospect["phone"] = person.get("phone")

    # Apollo information
    prospect["seniority"] = person.get(
        "seniority"
    )

    prospect["departments"] = person.get(
        "departments",
        []
    )

    prospect["functions"] = person.get(
        "functions",
        []
    )

    prospect["matchConfidence"] = person.get(
        "match_confidence"
    )

    prospect["photoUrl"] = person.get(
        "photo_url"
    )

    # Company information
    prospect["companyId"] = company.get("id")

    prospect["companySize"] = (
        company.get("employee_count")
        or ""
    )

    prospect["companyLinkedinUrl"] = (
        company.get("linkedin_url")
        or ""
    )

    # Detailed location
    prospect["city"] = location.get("city")
    prospect["state"] = location.get("state")
    prospect["country"] = location.get("country")

    return prospect


# For the Clay 

def clay_to_prospect(person: dict) -> dict | None:
    """
    Convert a Clay people-search result into the
    common RealGrowth prospect structure.
    """

    if not person:
        return None

    name = person.get("name")

    if not name:
        name = " ".join(
            filter(
                None,
                [
                    person.get("first_name"),
                    person.get("last_name"),
                ],
            )
        ).strip()

    if not name:
        return None

    linkedin_url = (
        person.get("url")
        or person.get("linkedin_url")
        or person.get("linkedinUrl")
        or person.get("linkedin")
    )

    company = (
        person.get("latest_experience_company")
        or person.get("company")
        or person.get("company_name")
    )

    title = (
        person.get("latest_experience_title")
        or person.get("title")
        or person.get("job_title")
        or person.get("jobTitle")
    )

    domain = person.get("domain")

    website = None

    if domain:
        domain = domain.strip()

        if domain.startswith("http://") or domain.startswith("https://"):
            website = domain
        else:
            website = f"https://{domain}"

    website = (
        person.get("website")
        or person.get("company_website")
        or website
    )

    location = person.get("structured_location") or {}

    if not isinstance(location, dict):
        location = {}

    city = location.get("city")
    state = location.get("state")
    country = location.get("country")

    provider_id = (
        person.get("id")
        or person.get("person_id")
        or person.get("personId")
    )

    if not provider_id and linkedin_url:
        provider_id = linkedin_url

    if not provider_id and name:
        provider_id = name.lower().strip()

    email = (
        person.get("email")
        or person.get("work_email")
        or person.get("business_email")
    )

    return {
        "provider": "clay",
        "providerId": str(provider_id),

        "name": name,
        "title": title,

        "email": email,
        "linkedinUrl": linkedin_url,

        "company": company,
        "website": website,

        "city": city,
        "state": state,
        "country": country,

        "source": "clay",
        "sourceEngine": "clay",

        "relationshipStage": "new",
        "relationshipScore": 0,
        "trustLevel": "unknown",
        "engagementScore": 0,

        "pipelineStage": "new",
        "stage": "new",

        "processing": False,
        "archived": False,
        "active": True,

        "discoveredFromFeed": False,
        "feedPostsCount": 0,
    }

# for the Google Maps

def google_maps_to_prospect(place: dict) -> dict | None:

    if not place:
        return None

    display_name = place.get("displayName") or {}

    name = display_name.get("text") or ""

    if not name:
        return None

    location = place.get("location") or {}

    prospect = build_base_prospect(
        name=name,
        title="",
        location=place.get("formattedAddress") or "",
        company=name,
        website=place.get("websiteUri") or "",
        industry=place.get("primaryType") or "",
        source="GOOGLE_MAPS",
        source_engine="GOOGLE_MAPS",
        search_url=place.get("googleMapsUri") or "",
    )

    prospect["provider"] = "google_maps"
    prospect["providerId"] = place.get("id")

    prospect["googleMapsUrl"] = place.get(
        "googleMapsUri"
    )

    prospect["googleMapsRating"] = place.get(
        "rating"
    )

    prospect["googleMapsUserRatingCount"] = place.get(
        "userRatingCount"
    )

    prospect["googlePlaceTypes"] = place.get(
        "types",
        []
    )

    prospect["phone"] = (
        place.get("nationalPhoneNumber")
        or place.get("internationalPhoneNumber")
    )

    prospect["latitude"] = location.get(
        "latitude"
    )

    prospect["longitude"] = location.get(
        "longitude"
    )

    return prospect