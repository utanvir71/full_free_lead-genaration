from __future__ import annotations

import json

from app.data.us_states import US_STATE_CODES


def build_restaurant_query(city: str, state: str, limit: int) -> str:
    normalized_state = state.upper()
    if normalized_state not in US_STATE_CODES:
        raise ValueError("state must be a two-letter U.S. state or DC code")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    if not city.strip():
        raise ValueError("city must not be blank")

    state_iso = f"US-{normalized_state}"
    city_value = json.dumps(city.strip())
    state_value = json.dumps(state_iso)

    return "\n".join(
        (
            "[out:json][timeout:25];",
            f'area["boundary"="administrative"]["admin_level"="4"]["ISO3166-2"={state_value}]->.state;',
            f'rel(area.state)["boundary"="administrative"]["name"={city_value}]->.city_boundary;',
            "map_to_area .city_boundary -> .city;",
            "(",
            '  node(area.city)["amenity"="restaurant"];',
            '  way(area.city)["amenity"="restaurant"];',
            '  relation(area.city)["amenity"="restaurant"];',
            ");",
            f"out tags center {limit};",
        )
    )
