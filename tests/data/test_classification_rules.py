def test_compensation_excluded_from_generic_ai_and_search():
    from core.classification import DataClassification, RULES
    rule = RULES[DataClassification.COMPENSATION]
    assert not rule.searchable and not rule.ai_allowed
    assert not rule.platform_default_access and not rule.support_default_access

def test_precise_location_excluded_from_generic_ai_and_search():
    from core.classification import DataClassification, RULES
    rule = RULES[DataClassification.PRECISE_LOCATION]
    assert not rule.searchable and not rule.ai_allowed
