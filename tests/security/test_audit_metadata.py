def test_audit_metadata_removes_protected_values():
    from security.audit_policy import AuditMetadataPolicy
    data = AuditMetadataPolicy.sanitize({
        'object_id': '123', 'latitude': '-1.944', 'longitude': '30.061',
        'salary': '1000', 'token': 'secret-token', 'private_message_body': 'private',
    })
    assert data == {'object_id': '123'}
