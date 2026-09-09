def register_workflow_adapters():
    from workflows.runtime_service import WorkflowTargetAdapterRegistry
    from reports.models import Report
    from reports.services import ReportWorkflowAdapter
    from forms_engine.models import FormSubmission
    from forms_engine.submission_service import FormSubmissionWorkflowAdapter
    from requests_app.models import BusinessRequest
    from requests_app.services import BusinessRequestWorkflowAdapter

    WorkflowTargetAdapterRegistry.register(Report, ReportWorkflowAdapter)
    WorkflowTargetAdapterRegistry.register(FormSubmission, FormSubmissionWorkflowAdapter)
    WorkflowTargetAdapterRegistry.register(BusinessRequest, BusinessRequestWorkflowAdapter)
