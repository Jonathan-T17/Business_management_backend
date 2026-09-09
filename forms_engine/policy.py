from core.redaction import FieldRedactionService
class FormSubmissionDisclosurePolicy:
    @staticmethod
    def schema_for(submission):
        return {f['key']:f.get('classification','NORMAL') for f in (getattr(submission,'schema_snapshot',None) or []) if isinstance(f,dict) and f.get('key')}
    @classmethod
    def data_for(cls,*,submission,user): return FieldRedactionService.redact_mapping(user=user,data=submission.data,schema=cls.schema_for(submission),owner_id=getattr(submission,'submitted_by_id',None))
