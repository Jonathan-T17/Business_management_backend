import pytest

def test_official_record_cannot_lower_source_classification():
    from records_management.policy import OfficialRecordClassificationPolicy
    class Source:
        classification='HR_CONFIDENTIAL'; sensitivity=None; category=None
    class Record:
        classification='NORMAL'
    with pytest.raises(ValueError):
        OfficialRecordClassificationPolicy.validate_snapshot_ceiling(source=Source(), record=Record())
