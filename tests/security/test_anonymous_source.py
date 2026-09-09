def test_anonymous_source_policy_removes_identity():
    from core.anonymity import AnonymousSourcePolicy
    value = AnonymousSourcePolicy.redact_mapping({
        'title': 'Anonymous incident',
        'created_by_email': 'person@example.test',
        'submitted_by_id': 'uuid',
        'status': 'SUBMITTED',
    })
    assert value == {'title': 'Anonymous incident', 'status': 'SUBMITTED'}
