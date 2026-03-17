def test_major_currencies_aliases():
    from afriflow.domains.shared import currency_map

    assert hasattr(currency_map, "MAJOR_CURRENCIES")
    assert hasattr(currency_map, "major_currencies")
    assert currency_map.MAJOR_CURRENCIES == currency_map.major_currencies
