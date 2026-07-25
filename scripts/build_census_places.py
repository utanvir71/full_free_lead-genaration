from __future__ import annotations

import csv
import io
import json
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

from app.data.us_states import US_STATE_FIPS_TO_CODE

SOURCE_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
    "2025_Gazetteer/2025_Gaz_place_national.zip"
)
OUTPUT_PATH = Path("app/data/us_census_places.json")
_LEGAL_SUFFIXES = (
    " city",
    " town",
    " village",
    " borough",
    " municipality",
    " CDP",
    " balance",
)


def _display_name(census_name: str) -> str:
    """Remove Census legal-designation suffixes used in its place names."""
    name = census_name.strip()
    for suffix in _LEGAL_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def main() -> None:
    with urllib.request.urlopen(SOURCE_URL) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))

    member = next(name for name in archive.namelist() if name.endswith(".txt"))
    places_by_state: dict[str, set[str]] = defaultdict(set)

    with archive.open(member) as raw_file:
        text_file = io.TextIOWrapper(raw_file, encoding="utf-8")
        for row in csv.DictReader(text_file, delimiter="|"):
            state_code = US_STATE_FIPS_TO_CODE.get(row["GEOID"][:2])
            place_name = _display_name(row["NAME"])
            if state_code is not None and place_name:
                places_by_state[state_code].add(place_name)

    payload = {
        "source": SOURCE_URL,
        "vintage": "2025",
        "places_by_state": {
            state: sorted(names, key=str.casefold)
            for state, names in sorted(places_by_state.items())
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
