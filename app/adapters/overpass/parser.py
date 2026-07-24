from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal, TypeGuard

from app.adapters.overpass.errors import OverpassPayloadError

OsmType = Literal["node", "way", "relation"]


@dataclass(frozen=True, slots=True)
class Candidate:
    osm_type: OsmType
    osm_id: int
    latitude: float
    longitude: float
    tags: Mapping[str, str]

    @property
    def source_identity(self) -> str:
        return f"osm:{self.osm_type}:{self.osm_id}"


def parse_elements(payload: Mapping[str, object]) -> list[Candidate]:
    elements = payload.get("elements")
    if not isinstance(elements, list):
        raise OverpassPayloadError("Overpass response must contain an elements list")

    candidates: list[Candidate] = []
    for element in elements:
        if not isinstance(element, Mapping):
            raise OverpassPayloadError("Overpass element must be an object")
        candidates.append(_parse_element(element))
    return candidates


def _parse_element(element: Mapping[object, object]) -> Candidate:
    osm_type = element.get("type")
    osm_id = element.get("id")
    if not _is_osm_type(osm_type) or not _is_int(osm_id):
        raise OverpassPayloadError("Overpass element is missing a supported identity")

    tags_value = element.get("tags", {})
    if not isinstance(tags_value, Mapping):
        raise OverpassPayloadError("Overpass element tags must be an object")
    tags = _parse_tags(tags_value)
    latitude, longitude = _parse_coordinates(element, osm_type)
    return Candidate(
        osm_type=osm_type,
        osm_id=osm_id,
        latitude=latitude,
        longitude=longitude,
        tags=MappingProxyType(tags),
    )


def _parse_tags(tags: Mapping[object, object]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for key, value in tags.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise OverpassPayloadError(
                "Overpass tags must contain string keys and values"
            )
        parsed[key] = value
    return parsed


def _parse_coordinates(
    element: Mapping[object, object], osm_type: OsmType
) -> tuple[float, float]:
    coordinates: Mapping[object, object]
    if osm_type == "node":
        coordinates = element
    else:
        center = element.get("center")
        if not isinstance(center, Mapping):
            raise OverpassPayloadError("Ways and relations require center geometry")
        coordinates = center

    latitude = coordinates.get("lat")
    longitude = coordinates.get("lon")
    if not _is_number(latitude) or not _is_number(longitude):
        raise OverpassPayloadError("Overpass element is missing coordinates")
    return float(latitude), float(longitude)


def _is_osm_type(value: object) -> TypeGuard[OsmType]:
    return value in {"node", "way", "relation"}


def _is_int(value: object) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: object) -> TypeGuard[int | float]:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
