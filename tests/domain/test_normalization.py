from app.domain.normalization import (
    normalize_address,
    normalize_domain,
    normalize_osm_identity,
    normalize_phone,
)


def test_normalizers_create_conservative_comparison_keys() -> None:
    assert normalize_osm_identity("node", 123) == "node:123"
    assert normalize_domain("https://www.menu.example.com/dinner") == "example.com"
    assert normalize_phone("(512) 555-0199") == "+15125550199"
    assert (
        normalize_address("123  Main St., Austin, TX 78701")
        == "123 main st austin tx 78701"
    )


def test_normalizers_do_not_create_keys_for_missing_or_invalid_values() -> None:
    assert normalize_domain("not a URL") is None
    assert normalize_phone("call us") is None
    assert normalize_address("") is None
