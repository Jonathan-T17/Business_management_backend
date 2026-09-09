from core.anonymity import AnonymousSourcePolicy
from core.redaction import FieldRedactionService
class ReportDisclosurePolicy:
    @staticmethod
    def dynamic_schema(report): return {f.key:getattr(f,'classification','NORMAL') for f in report.fields.all()}
    @classmethod
    def serialize_dynamic_values(cls,*,report,user): return FieldRedactionService.redact_mapping(user=user,data={f.key:f.value for f in report.fields.all()},schema=cls.dynamic_schema(report))
    @staticmethod
    def author_for(*,report,user): return AnonymousSourcePolicy.display_identity(obj=report,viewer=user)
