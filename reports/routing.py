from rest_framework.exceptions import ValidationError


class ReportRoutingService:
    @classmethod
    def resolve(cls, *, report, actor):
        """Resolve configured workflow; submitters cannot choose arbitrary routes."""
        from company_setup.models import ReportingProcess

        process = ReportingProcess.objects.filter(
            company=report.company,
            is_active=True,
            form_template__isnull=True,
        ).filter(report_type=getattr(report, "report_type", "GENERAL")).select_related("approval_route__workflow").first()
        workflow = process.approval_route.workflow if process and process.approval_route_id else None
        if not workflow:
            # Compatibility fallback until every legacy report type is configured.
            from workflows.models import WorkflowDefinition
            workflow = WorkflowDefinition.objects.filter(
                company=report.company,
                target_type="REPORT",
                lifecycle_status="PUBLISHED",
                is_active=True,
                is_default=True,
            ).order_by("-version").first()
        if not workflow:
            raise ValidationError("No published report approval route is configured.")
        return workflow
