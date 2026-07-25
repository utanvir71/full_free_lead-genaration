from app.adapters.overpass.query import build_restaurant_query


def test_builds_a_state_scoped_restaurant_only_query() -> None:
    query = build_restaurant_query(city="Austin", state="TX", limit=30)

    assert '["ISO3166-2"="US-TX"]' in query
    assert '["name"="Austin"]' in query
    assert (
        'area(area.state)["boundary"="administrative"]["name"="Austin"]->.city;'
        in query
    )
    assert "map_to_area" not in query
    assert 'node(area.city)["amenity"="restaurant"];' in query
    assert 'way(area.city)["amenity"="restaurant"];' in query
    assert 'relation(area.city)["amenity"="restaurant"];' in query
    assert 'out tags center 30;' in query


def test_escapes_city_values_and_rejects_invalid_state_or_limit() -> None:
    query = build_restaurant_query(city='St. "John\\s"', state="CA", limit=1)

    assert '["name"="St. \\"John\\\\s\\""]' in query

    for state in ("C", "ZZ", "California"):
        try:
            build_restaurant_query(city="Austin", state=state, limit=30)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected {state!r} to be rejected")

    for limit in (0, 101):
        try:
            build_restaurant_query(city="Austin", state="TX", limit=limit)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected {limit} to be rejected")
