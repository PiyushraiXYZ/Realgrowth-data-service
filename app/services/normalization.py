def normalize_google_place(place: dict) -> dict:
    display_name = place.get("displayName") or {}
    location = place.get("location") or {}

    return {
        "provider": "google_maps",
        "provider_id": place.get("id"),

        "name": display_name.get("text"),

        "address": place.get("formattedAddress"),

        "website": place.get("websiteUri"),

        "phone": (
            place.get("internationalPhoneNumber")
            or place.get("nationalPhoneNumber")
        ),

        "google_maps_url": place.get("googleMapsUri"),

        "category": place.get("primaryType"),

        "types": place.get("types", []),

        "rating": place.get("rating"),

        "review_count": place.get(
            "userRatingCount"
        ),

        "location": {
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
        },
    }


def normalize_google_places(places: list) -> list:
    return [
        normalize_google_place(place)
        for place in places
        if place
    ]