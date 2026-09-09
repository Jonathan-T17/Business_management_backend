from core.data_classification import DataClassification


class OfficialRecordFinalizer:
    """Build authoritative, source-aware record snapshots."""

    @classmethod
    def finalize(cls, *, source, actor, request=None, trigger_status=None):
        label = source._meta.app_label
        if label == "reports":
            return cls._report(source=source, actor=actor, request=request, trigger_status=trigger_status)
        if label == "forms_engine":
            return cls._form(source=source, actor=actor, request=request, trigger_status=trigger_status)
        if label == "requests_app":
            return cls._request(source=source, actor=actor, request=request, trigger_status=trigger_status)
        if label == "planning":
            return cls._plan(source=source, actor=actor, request=request, trigger_status=trigger_status)
        if label == "field_operations":
            return cls._field(source=source, actor=actor, request=request, trigger_status=trigger_status)
        return None

    @classmethod
    def _workflow_snapshot(cls, source):
        from workflows.models import WorkflowInstance
        instance = WorkflowInstance.objects.filter(
            content_type__app_label=source._meta.app_label,
            content_type__model=source._meta.model_name,
            object_id=str(source.pk),
        ).order_by("-started_at").first()
        if not instance:
            return []
        return [{
            "order": step.order,
            "step": step.name,
            "status": step.status,
            "recipients": [
                {"user_id": str(r.user_id), "status": r.status, "acted_at": r.acted_at.isoformat() if r.acted_at else None}
                for r in step.recipients.all()
            ],
        } for step in instance.steps.prefetch_related("recipients").all()]

    @classmethod
    def _issue(cls, *, source, actor, record_type, title, snapshot, classification, request, trigger_status):
        from .services import OfficialRecordService
        return OfficialRecordService.issue_if_configured(
            source=source,
            record_type=record_type,
            status=trigger_status or getattr(source, "status", ""),
            actor=actor,
            title=title,
            snapshot=snapshot,
            approval_snapshot=cls._workflow_snapshot(source),
            branch=getattr(source, "branch", None),
            request=request,
            classification=classification,
            source_version=getattr(source, "version", 1),
        )

    @classmethod
    def _report(cls, *, source, actor, request, trigger_status):
        fields = []
        classes = [getattr(source, "sensitivity", DataClassification.NORMAL)]
        for field in source.fields.all():
            classification = getattr(field, "classification", DataClassification.NORMAL)
            classes.append(classification)
            fields.append({"key": field.key, "value": field.value, "classification": classification})
        snapshot = {
            "report_number": source.report_number,
            "title": source.title,
            "report_type": source.report_type,
            "reporting_date": str(source.reporting_date),
            "status": source.status,
            "visibility": source.visibility,
            "fields": fields,
        }
        return cls._issue(source=source, actor=actor, record_type="REPORT", title=source.title, snapshot=snapshot, classification=DataClassification.max_classification(classes), request=request, trigger_status=trigger_status)

    @classmethod
    def _form(cls, *, source, actor, request, trigger_status):
        schema = getattr(source, "schema_snapshot", {}) or {}
        classes = [f.get("classification", DataClassification.NORMAL) for f in schema.get("fields", [])]
        snapshot = {
            "reference_number": source.reference_number,
            "title": source.title,
            "template_id": str(source.template_id),
            "template_version": getattr(source, "template_version", getattr(source.template, "version", 1)),
            "reporting_date": str(source.reporting_date),
            "status": source.status,
            "schema": schema,
            "data": source.data,
        }
        return cls._issue(source=source, actor=actor, record_type="FORM_SUBMISSION", title=source.title or source.reference_number, snapshot=snapshot, classification=DataClassification.max_classification(classes), request=request, trigger_status=trigger_status)

    @classmethod
    def _request(cls, *, source, actor, request, trigger_status):
        classification = (getattr(source, "request_type_snapshot", {}) or {}).get("classification", DataClassification.NORMAL)
        snapshot = {
            "request_number": source.request_number,
            "request_type": getattr(source, "request_type_snapshot", {}) or source.request_type,
            "title": source.title,
            "description": source.description,
            "amount": str(source.amount) if source.amount is not None else None,
            "currency": source.currency,
            "quantity": str(source.quantity) if source.quantity is not None else None,
            "unit": source.unit,
            "needed_by": str(source.needed_by) if source.needed_by else None,
            "status": source.status,
        }
        return cls._issue(source=source, actor=actor, record_type="REQUEST", title=source.title, snapshot=snapshot, classification=classification, request=request, trigger_status=trigger_status)

    @classmethod
    def _plan(cls, *, source, actor, request, trigger_status):
        snapshot = {"title": source.title, "description": source.description, "plan_type": source.plan_type, "status": source.status, "start_date": str(source.start_date), "end_date": str(source.end_date)}
        return cls._issue(source=source, actor=actor, record_type="PLAN", title=source.title, snapshot=snapshot, classification=DataClassification.MANAGEMENT_CONFIDENTIAL if source.visibility == "MANAGEMENT" else DataClassification.NORMAL, request=request, trigger_status=trigger_status)

    @classmethod
    def _field(cls, *, source, actor, request, trigger_status):
        snapshot = {"title": source.title, "activity_type": source.activity_type, "activity_date": str(source.activity_date), "status": source.status, "stops": [{"sequence": s.sequence, "stop_type": s.stop_type, "location_name": s.location_name, "status": s.status} for s in source.stops.all()]}
        # Exact coordinates are intentionally not copied into ordinary official snapshots.
        return cls._issue(source=source, actor=actor, record_type="FIELD_SUMMARY", title=source.title, snapshot=snapshot, classification=DataClassification.PERSONAL, request=request, trigger_status=trigger_status)
