from datetime import UTC, datetime

from app.adapters.crawler.fetcher import FetchedPage
from app.adapters.extraction.business import BusinessExtractor
from app.adapters.overpass.parser import Candidate
from app.domain.enums import FactState

OSM_CAPTURED_AT = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)
WEBSITE_CAPTURED_AT = datetime(2026, 7, 25, 12, 5, tzinfo=UTC)


def test_business_extractor_keeps_conflicting_osm_and_json_ld_facts_separate() -> None:
    candidate = Candidate(
        osm_type="node",
        osm_id=42,
        latitude=30.2672,
        longitude=-97.742,
        tags={
            "name": "Rosa's Kitchen",
            "addr:housenumber": "100",
            "addr:street": "Main St",
            "addr:city": "Austin",
            "addr:state": "TX",
            "addr:postcode": "78701",
            "phone": "+1-512-555-0100",
            "website": "https://rosa.example",
            "cuisine": "mexican",
            "opening_hours": "Mo-Sa 11:00-22:00",
        },
    )
    page = FetchedPage(
        url="https://rosa.example/locations",
        html="""
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Restaurant",
          "name": "Rosa Kitchen & Bar",
          "address": {
            "streetAddress": "101 Main Street",
            "addressLocality": "Austin",
            "addressRegion": "TX",
            "postalCode": "78701"
          },
          "telephone": "+1-512-555-0199",
          "url": "https://rosa.example",
          "servesCuisine": ["Mexican", "Cocktails"],
          "openingHours": "Mo-Sa 11:00-23:00",
          "geo": {"latitude": 30.2673, "longitude": -97.7419},
          "location": {
            "@type": "Restaurant",
            "name": "Rosa South",
            "address": "200 South Street, Austin, TX"
          }
        }
        </script>
        """,
        http_status=200,
        fetched_at=WEBSITE_CAPTURED_AT,
    )

    facts = BusinessExtractor().extract(candidate, (page,), captured_at=OSM_CAPTURED_AT)

    names = [fact for fact in facts if fact.fact_type == "name"]
    assert {(fact.value, fact.source) for fact in names} == {
        ("Rosa's Kitchen", "osm:node:42"),
        ("Rosa Kitchen & Bar", "https://rosa.example/locations"),
    }
    assert all(fact.state is FactState.PRESENT for fact in facts)
    assert ("coordinates", "30.2672,-97.742", "osm:node:42") in {
        (fact.fact_type, fact.value, fact.source) for fact in facts
    }
    assert ("locations", "Rosa South | 200 South Street, Austin, TX") in {
        (fact.fact_type, fact.value) for fact in facts
    }
    assert all(fact.excerpt for fact in facts)


def test_business_extractor_represents_missing_osm_fields_as_unknown() -> None:
    candidate = Candidate(
        osm_type="way",
        osm_id=43,
        latitude=30.2,
        longitude=-97.7,
        tags={},
    )

    facts = BusinessExtractor().extract(candidate, (), captured_at=OSM_CAPTURED_AT)

    assert {fact.fact_type for fact in facts} == {
        "name",
        "address",
        "phone",
        "website",
        "cuisine",
        "hours",
        "coordinates",
        "locations",
    }
    assert {
        (fact.fact_type, fact.state, fact.value) for fact in facts
    } == {
        ("name", FactState.UNKNOWN, None),
        ("address", FactState.UNKNOWN, None),
        ("phone", FactState.UNKNOWN, None),
        ("website", FactState.UNKNOWN, None),
        ("cuisine", FactState.UNKNOWN, None),
        ("hours", FactState.UNKNOWN, None),
        ("coordinates", FactState.PRESENT, "30.2,-97.7"),
        ("locations", FactState.UNKNOWN, None),
    }
    assert {fact.source for fact in facts} == {"osm:way:43"}
