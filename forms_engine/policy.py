from core.redaction import FieldRedactionService
class FormSubmissionDisclosurePolicy:
    @classmethod
    def restore_masked_answers(cls, *, submission, user, data):
        """Keep undisclosed values when a client returns its masked representation."""
        from copy import deepcopy
        from core.redaction import REDACTED
        answers = deepcopy(data)
        disclosed = cls.data_for(submission=submission, user=user)
        for key, value in answers.items():
            if value == REDACTED and disclosed.get(key) == REDACTED and key in submission.data:
                answers[key] = deepcopy(submission.data[key])
        return answers

    @staticmethod
    def schema_for(submission):
        snapshot = getattr(submission, 'schema_snapshot', None) or {}
        fields = snapshot.get('fields', []) if isinstance(snapshot, dict) else snapshot
        return {f['key']:f.get('classification','NORMAL') for f in fields if isinstance(f,dict) and f.get('key')}
    @classmethod
    def data_for(cls,*,submission,user): return FieldRedactionService.redact_mapping(user=user,data=submission.data,schema=cls.schema_for(submission),owner_id=getattr(submission,'submitted_by_id',None))
