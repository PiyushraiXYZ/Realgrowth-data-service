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