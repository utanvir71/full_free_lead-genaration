import json
from pathlib import Path

import pytest

from app.adapters.overpass.errors import OverpassPayloadError
from app.adapters.overpass.parser import parse_elements

FIXTURE_PATH = Path(__file__).parents[2] / "fixtures" / "overpass" / "restaurants.json"


def test_parse_elements_preserves_osm_identity_tags_and_geometry() -> None:
    candidates = parse_elements(json.loads(FIXTURE_PATH.read_text()))

    assert [(candidate.osm_type, candidate.osm_id) for candidate in candidates] == [
        ("node", 101),
        ("way", 202),
        ("relation", 303),
    ]
    assert candidates[0].latitude == 30.2672
    assert candidates[1].longitude == -97.744
    assert candidates[0].tags["website"] == "https://northstar.example"
    assert candidates[2].source_identity == "osm:relation:303"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"elements": "not-a-list"},
        {"elements": [{"type": "node", "id": 1, "tags": {}}]},
    ],
)
def test_parse_elements_rejects_invalid_payloads(payload: dict[str, object]) -> None:
    with pytest.raises(OverpassPayloadError):
        parse_elements(payload)
