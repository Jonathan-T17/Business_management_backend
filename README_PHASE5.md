# SmartBiz Phase 5 — Business Process Engine

This package is an integration overlay for Reports, Workflows, Forms Engine, Reporting Schedules and Business Requests.
It is intentionally designed around business invariants rather than per-view role checks.

## New required schema fields

### workflows.WorkflowDefinition
- lifecycle_status: DRAFT / PUBLISHED / ARCHIVED
- version: PositiveIntegerField(default=1)
- supersedes: nullable self FK (PROTECT/SET_NULL according to migration policy)
- is_default: BooleanField(default=False)
- published_at / published_by recommended
- unique constraint should include company + code + version, not company + code alone

### workflows.WorkflowInstance
- workflow_version: PositiveIntegerField
- runtime target uniqueness: add a constraint/index supporting one active instance per target (application locking remains required)

### workflows.WorkflowStepInstance
- routing_snapshot: JSONField(default=dict)

### forms_engine.FormTemplate
- lifecycle_status already exists; make versioned records immutable after publish/use
- supersedes: nullable self FK
- unique (company, code, version)

### forms_engine.FormField
- classification: CharField using core.data_classification.DataClassification

### forms_engine.FormSubmission
- enforce template_version
- schema_snapshot is authoritative for validation/display history
- unique (company, reference_number)

### reports.Report
- unique (company, report_number)
- sensitivity/classification field
- generic status/timestamps read-only through serializer

### reports.ReportField
- classification field (or replace free-form fields with a structured schema snapshot)

### requests_app.BusinessRequest
- request_type_definition FK to company_setup.RequestTypeDefinition (PROTECT)
- request_type_snapshot JSON
- workflow becomes server-controlled/read-only
- unique (company, request_number) already exists/should remain
- classification derived from RequestTypeDefinition

### company_setup.RequestTypeDefinition
- classification
- optional required_view_capability
- fulfillment capability/policy if per-type fulfillment differs
- workflow must be a published REQUEST workflow

### reporting_schedules.ReportingObligation
- template_version
- reminder event timestamps or a separate ReminderDelivery model with unique event keys

## API rules

1. Generic PATCH may edit only DRAFT/RETURNED source objects owned by the author.
2. Status changes are explicit actions and run through services.
3. Submitters never provide workflow IDs for normal submission.
4. Published forms/workflows are immutable. Editing creates a new draft version.
5. Workflow runtime copies routing metadata and resolved recipients.
6. Workflow finalization uses a source adapter; the workflow engine never blindly writes arbitrary `target.status`.
7. Dynamic fields carry classification metadata.
8. Official Records inherit source sensitivity and use source-owned snapshot builders.
9. Reporting schedules use company timezone for business dates/deadlines and UTC for stored timestamps.
10. Late submission policy is enforced during submission, not only displayed in the UI.
11. Business identifiers use a row-locked company sequence, not `count()+1`.
12. Configuration authority, content visibility, approval authority and fulfillment authority remain separate.

## Integration actions

- Replace Report serializer generic create/update with ReportLifecycleService.
- Report `/submit/` takes no workflow argument.
- Replace WorkflowService.start/approve/reject/return internals with WorkflowRuntimeService equivalents, retaining the existing recipient resolver temporarily.
- Implement reject/return with the same row-locking approach as approve.
- Replace workflow definition CRUD with WorkflowDefinitionService; archive instead of deleting used definitions.
- Replace FormTemplate serializer destructive updates and reorder on published forms with FormTemplateVersionService.
- Pin all FormSubmission drafts to the exact template version/schema snapshot.
- Replace BusinessRequest serializer create/update with BusinessRequestLifecycleService.
- Make BusinessRequest.workflow read-only.
- Add RequestTypeDefinition FK and migrate legacy request_type values by company+code.
- Replace ReportingScheduleService deadline calculations with the company timezone service.
- Change overdue command to include linked DRAFT submissions.
- Move management commands to production scheduler/worker infrastructure later; users never run commands.

## Required test matrix before Phase 5 is accepted

### Workflows
- tenant isolation and platform boundary
- target/model mismatch rejected
- published version cannot mutate
- optional no-recipient step is SKIPPED
- required no-recipient step fails start
- ANY and ALL behavior
- concurrent approvals do not double-complete
- delegated approval recorded accurately
- reject/return reason and state transitions
- notification flags respected
- source sensitivity preserved

### Forms
- branch/department/team eligibility
- published template cannot mutate/reorder
- revision creates new draft version
- old submission preserves old schema
- dynamic field classification validation
- LOCATION cannot silently be NORMAL
- author-only DRAFT/RETURNED edit/delete
- configured workflow cannot be overridden

### Reporting schedules
- Kigali/New York/Tokyo company timezone cases
- daily/weekly/monthly/custom rules
- idempotent obligation generation
- concurrent generation no duplicates
- late submission allowed/disallowed
- linked draft becomes MISSED after deadline
- reminder delivery idempotency
- template version pinned

### Requests
- request type configuration authoritative
- client workflow override ignored/rejected
- HR/financial classifications preserve restricted visibility
- requester-only edit in DRAFT/RETURNED
- approval != fulfillment authority
- numbering concurrency
- company default currency
- attachment-required/forbidden rules

### Reports
- creation remains DRAFT
- submission notification only on submit
- author-only edit while DRAFT/RETURNED
- anonymous identity remains redacted in non-authoritative secondary systems
- private/sensitive report excluded from analytics/search/export unless explicitly permitted
- report numbering concurrency
- configured route cannot be overridden

## Important next integration dependency

`records_management.finalizers.OfficialRecordFinalizer` is referenced as the target production interface and will be implemented in Phase 6 together with Documents, Field Operations, Planning and Official Records.
