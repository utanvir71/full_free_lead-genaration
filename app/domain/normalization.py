from __future__ import annotations

import re
from urllib.parse import urlparse

import tldextract

_EXTRACT = tldextract.TLDExtract(suffix_list_urls=())


def normalize_osm_identity(osm_type: str, osm_id: int) -> str:
    if osm_type not in {"node", "way", "relation"} or osm_id < 1:
        raise ValueError("OSM identity must be a supported positive element ID")
    return f"{osm_type}:{osm_id}"


def normalize_domain(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    extracted = _EXTRACT(parsed.hostname)
    if not extracted.domain or not extracted.suffix:
        return None
    return f"{extracted.domain}.{extracted.suffix}".casefold()


def normalize_phone(value: str) -> str | None:
    digits = "".join(character for character in value if character.isdigit())
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return None


def normalize_address(value: str) -> str | None:
    normalized = re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()
    return normalized or None
