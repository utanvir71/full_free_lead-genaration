from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from hashlib import sha256
from html.parser import HTMLParser

from app.adapters.crawler.fetcher import FetchedPage
from app.adapters.overpass.parser import Candidate
from app.domain.enums import FactState, ValidationState
from app.domain.models import Fact, FactValue

_BUSINESS_FACT_TYPES = (
    "name",
    "address",
    "phone",
    "website",
    "cuisine",
    "hours",
    "coordinates",
    "locations",
)


class BusinessExtractor:
    def __init__(self, *, extractor_version: str = "business-facts-v1") -> None:
        self._extractor_version = extractor_version

    def extract(
        self,
        candidate: Candidate,
        pages: Sequence[FetchedPage],
        *,
        captured_at: datetime,
    ) -> list[Fact]:
        facts = self._osm_facts(candidate, captured_at)
        for page in pages:
            for item in _restaurant_json_ld(page.html):
                facts.extend(self._website_facts(item, page))
        return facts

    def _osm_facts(self, candidate: Candidate, captured_at: datetime) -> list[Fact]:
        tags = candidate.tags
        address = _osm_address(tags)
        values: dict[str, FactValue] = {
            "name": tags.get("name"),
            "address": address,
            "phone": tags.get("phone") or tags.get("contact:phone"),
            "website": tags.get("website") or tags.get("contact:website"),
            "cuisine": tags.get("cuisine"),
            "hours": tags.get("opening_hours"),
            "coordinates": _coordinates(candidate.latitude, candidate.longitude),
            "locations": address,
        }
        facts: list[Fact] = []
        for fact_type in _BUSINESS_FACT_TYPES:
            value = values[fact_type]
            facts.append(
                self._fact(
                    fact_type=fact_type,
                    value=value,
                    source=candidate.source_identity,
                    excerpt=(
                        f"{fact_type}: {value}"
                        if value is not None
                        else f"OSM candidate has no {fact_type} tag"
                    ),
                    captured_at=captured_at,
                )
            )
        return facts

    def _website_facts(
        self, item: Mapping[str, object], page: FetchedPage
    ) -> list[Fact]:
        values: list[tuple[str, FactValue]] = []
        for field, fact_type in (
            ("name", "name"),
            ("telephone", "phone"),
            ("url", "website"),
        ):
            value = _text(item.get(field))
            if value is not None:
                values.append((fact_type, value))

        address = _address(item.get("address"))
        if address is not None:
            values.append(("address", address))
            values.append(("locations", address))
        values.extend(
            ("cuisine", cuisine) for cuisine in _texts(item.get("servesCuisine"))
        )
        values.extend(("hours", hours) for hours in _opening_hours(item))
        coordinates = _geo_coordinates(item.get("geo"))
        if coordinates is not None:
            values.append(("coordinates", coordinates))
        values.extend(
            ("locations", location) for location in _locations(item.get("location"))
        )

        return [
            self._fact(
                fact_type=fact_type,
                value=value,
                source=page.url,
                excerpt=f"JSON-LD {fact_type}: {value}",
                captured_at=page.fetched_at,
            )
            for fact_type, value in values
        ]

    def _fact(
        self,
        *,
        fact_type: str,
        value: FactValue,
        source: str,
        excerpt: str,
        captured_at: datetime,
    ) -> Fact:
        state = FactState.PRESENT if value is not None else FactState.UNKNOWN
        identity = "\n".join((source, fact_type, str(value), self._extractor_version))
        return Fact(
            fact_id=f"fact:{sha256(identity.encode()).hexdigest()}",
            fact_type=fact_type,
            state=state,
            value=value,
            source=source,
            excerpt=excerpt,
            captured_at=captured_at,
            extractor_version=self._extractor_version,
            validation_state=ValidationState.NOT_APPLICABLE,
        )


class _JsonLdParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_json_ld = False
        self._parts: list[str] = []
        self.documents: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script" and (dict(attrs).get("type") or "").casefold() == (
            "application/ld+json"
        ):
            self._in_json_ld = True
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._in_json_ld:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._in_json_ld:
            self.documents.append("".join(self._parts))
            self._parts = []
            self._in_json_ld = False


def _restaurant_json_ld(html: str) -> list[Mapping[str, object]]:
    parser = _JsonLdParser()
    parser.feed(html)
    parser.close()
    items: list[Mapping[str, object]] = []
    for document in parser.documents:
        try:
            parsed = json.loads(document)
        except json.JSONDecodeError:
            continue
        for item in _json_ld_objects(parsed):
            if _is_restaurant(item):
                items.append(item)
    return items


def _json_ld_objects(value: object) -> Iterable[Mapping[str, object]]:
    if isinstance(value, Mapping):
        typed = {str(key): item for key, item in value.items()}
        yield typed
        graph = typed.get("@graph")
        if graph is not None:
            yield from _json_ld_objects(graph)
    elif isinstance(value, list):
        for item in value:
            yield from _json_ld_objects(item)


def _is_restaurant(item: Mapping[str, object]) -> bool:
    raw_type = item.get("@type")
    types = _texts(raw_type)
    return any(
        item_type.casefold() in {"restaurant", "foodestablishment"}
        for item_type in types
    )


def _osm_address(tags: Mapping[str, str]) -> str | None:
    values = [
        " ".join(filter(None, (tags.get("addr:housenumber"), tags.get("addr:street")))),
        ", ".join(
            filter(
                None,
                (
                    tags.get("addr:city"),
                    " ".join(
                        filter(
                            None,
                            (tags.get("addr:state"), tags.get("addr:postcode")),
                        )
                    ),
                ),
            )
        ),
        tags.get("addr:country"),
    ]
    address = ", ".join(value for value in values if value)
    return address or None


def _address(value: object) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if not isinstance(value, Mapping):
        return None
    parts = [
        _text(value.get("streetAddress")),
        _text(value.get("addressLocality")),
        " ".join(
            filter(
                None,
                (_text(value.get("addressRegion")), _text(value.get("postalCode"))),
            )
        ),
        _text(value.get("addressCountry")),
    ]
    result = ", ".join(part for part in parts if part)
    return result or None


def _geo_coordinates(value: object) -> str | None:
    if not isinstance(value, Mapping):
        return None
    latitude = value.get("latitude")
    longitude = value.get("longitude")
    if isinstance(latitude, (int, float)) and isinstance(longitude, (int, float)):
        return _coordinates(latitude, longitude)
    return None


def _coordinates(latitude: int | float, longitude: int | float) -> str:
    return f"{latitude},{longitude}"


def _locations(value: object) -> list[str]:
    raw_locations: list[object] = value if isinstance(value, list) else [value]
    locations: list[str] = []
    for location in raw_locations:
        if isinstance(location, str):
            locations.append(location)
        elif isinstance(location, Mapping):
            name = _text(location.get("name"))
            address = _address(location.get("address"))
            if name and address:
                locations.append(f"{name} | {address}")
            elif name or address:
                locations.append(name or address or "")
    return locations


def _opening_hours(item: Mapping[str, object]) -> list[str]:
    hours = _texts(item.get("openingHours"))
    specifications = item.get("openingHoursSpecification")
    raw_specifications = (
        specifications if isinstance(specifications, list) else [specifications]
    )
    for specification in raw_specifications:
        if not isinstance(specification, Mapping):
            continue
        days = ", ".join(_texts(specification.get("dayOfWeek")))
        opens = _text(specification.get("opens"))
        closes = _text(specification.get("closes"))
        span = "-".join(part for part in (opens, closes) if part)
        value = " ".join(part for part in (days, span) if part)
        if value:
            hours.append(value)
    return hours


def _texts(value: object) -> list[str]:
    if isinstance(value, list):
        return [text for item in value if (text := _text(item)) is not None]
    text = _text(value)
    return [text] if text is not None else []


def _text(value: object) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None
