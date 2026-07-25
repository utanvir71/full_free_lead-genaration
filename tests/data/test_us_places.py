from app.data.us_places import cities_for_state, is_census_place


def test_texas_census_places_include_austin_without_legal_suffix() -> None:
    assert "Austin" in cities_for_state("TX")
    assert is_census_place("Austin", "TX")


def test_a_census_place_is_rejected_for_a_different_state() -> None:
    assert not is_census_place("Austin", "CA")
