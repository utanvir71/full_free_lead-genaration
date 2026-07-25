from __future__ import annotations

import json
from functools import cache
from pathlib import Path

_DATA_PATH = Path(__file__).with_name("us_census_places.json")


@cache
def _places_by_state() -> dict[str, tuple[str, ...]]:
    payload = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    raw_places = payload["places_by_state"]
    return {
        state: tuple(cities)
        for state, cities in raw_places.items()
    }


def cities_for_state(state: str) -> tuple[str, ...]:
    return _places_by_state().get(state.upper(), ())


def is_census_place(city: str, state: str) -> bool:
    normalized_city = city.strip().casefold()
    return any(
        candidate.casefold() == normalized_city
        for candidate in cities_for_state(state)
    )