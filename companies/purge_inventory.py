"""Explicit ownership inventory. New tenant models block purge until reviewed.

User identities are retained, disabled and detached. Workspace deletion removes
company membership and business records, not the person's global identity.
"""
DIRECT = frozenset("""
companies.branch companies.companyinvite
organizations.department organizations.team organizations.position organizations.employeeprofile
organizations.usercapabilitygrant organizations.positioncapabilitygrant organizations.employeecompensation
organizations.employeedelegation organizations.employeereplacement organizations.employeepositionassignment
security.auditlog security.activesession security.loginhistory security.failedloginattempt security.supportaccesssession
projects.project tasks.task reports.report notifications.notification notifications.emaildeliverylog
subscriptions.subscription analytics_ai.aianalyticsrecord analytics_ai.analyticssnapshot analytics_ai.aiinsight
activity.activitylog comments.comment chat.conversation workflows.workflowdefinition workflows.workflowinstance
forms_engine.formtemplate forms_engine.formsubmission documents.attachment documents.documentcategory documents.document
reporting_schedules.reportingschedule reporting_schedules.reportingobligation planning.companyplan
requests_app.businessrequest field_operations.fieldactivity records_management.officialrecord
records_management.recordexport records_management.recordsequence data_tools.importjob data_tools.dataexportlog
company_setup.companysetupstate company_setup.rolepreset company_setup.requesttypedefinition
company_setup.fieldactivitytemplate company_setup.approvalroute company_setup.reportingprocess
company_setup.officialrecordpolicy company_setup.notificationpolicy support.supportticket
""".split())

CHILDREN = {
    "organizations.employeetransfer": "employee__company_id",
    "organizations.employeenote": "employee__company_id",
    "organizations.employeepositionassignment_branches": "employeepositionassignment__company_id",
    "projects.project_branches": "project__company_id",
    "projects.projectmembership": "project__company_id",
    "tasks.task_assignees": "task__company_id",
    "tasks.taskactivity": "task__company_id",
    "reports.reportfield": "report__company_id",
    "reports.reportcomment": "report__company_id",
    "chat.conversationmember": "conversation__company_id",
    "chat.message": "conversation__company_id",
    "workflows.workflowstepdefinition": "workflow__company_id",
    "workflows.workflowstepinstance": "workflow_instance__company_id",
    "workflows.workflowsteprecipient": "step__workflow_instance__company_id",
    "workflows.workflowactionlog": "workflow_instance__company_id",
    "forms_engine.formfield": "template__company_id",
    "forms_engine.materialjourney": "submission__company_id",
    "forms_engine.materialmovement": "journey__submission__company_id",
    "documents.documentversion": "document__company_id",
    "planning.planitem": "plan__company_id",
    "field_operations.fieldstop": "activity__company_id",
    "field_operations.fieldstopmetric": "stop__activity__company_id",
    "support.supportmessage": "ticket__company_id",
}

RETAINED_COMPANY_MODELS = frozenset({"platform_admin.securityincident"})
