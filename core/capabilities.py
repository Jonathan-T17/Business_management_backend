class Capabilities:
    # People & organization
    VIEW_ALL_EMPLOYEES = "VIEW_ALL_EMPLOYEES"
    MANAGE_EMPLOYEES = "MANAGE_EMPLOYEES"
    MANAGE_ORGANIZATION = "MANAGE_ORGANIZATION"

    # Reporting / approvals / forms
    VIEW_ALL_REPORTS = "VIEW_ALL_REPORTS"
    APPROVE_REPORTS = "APPROVE_REPORTS"
    RECEIVE_REPORTS = "RECEIVE_REPORTS"
    MODERATE_REPORT_COMMENTS = "MODERATE_REPORT_COMMENTS"
    APPROVE_REQUESTS = "APPROVE_REQUESTS"
    FULFILL_REQUESTS = "FULFILL_REQUESTS"
    REVIEW_SUBMISSIONS = "REVIEW_SUBMISSIONS"
    USE_FORMS = "USE_FORMS"
    MANAGE_FORM_TEMPLATES = "MANAGE_FORM_TEMPLATES"
    PUBLISH_FORM_TEMPLATES = "PUBLISH_FORM_TEMPLATES"
    MANAGE_WORKFLOWS = "MANAGE_WORKFLOWS"
    PUBLISH_WORKFLOWS = "PUBLISH_WORKFLOWS"
    MANAGE_REPORTING_SCHEDULES = "MANAGE_REPORTING_SCHEDULES"
    MANAGE_REQUEST_TYPES = "MANAGE_REQUEST_TYPES"

    # Projects / tasks / planning
    MANAGE_PROJECTS = "MANAGE_PROJECTS"
    MANAGE_TASKS = "MANAGE_TASKS"
    VIEW_COMPANY_PLANS = "VIEW_COMPANY_PLANS"
    VIEW_MANAGEMENT_PLANS = "VIEW_MANAGEMENT_PLANS"
    MANAGE_COMPANY_PLANS = "MANAGE_COMPANY_PLANS"

    # Documents / official records
    MANAGE_DOCUMENTS = "MANAGE_DOCUMENTS"
    VIEW_MANAGEMENT_DOCUMENTS = "VIEW_MANAGEMENT_DOCUMENTS"
    VIEW_OFFICIAL_RECORDS = "VIEW_OFFICIAL_RECORDS"
    ISSUE_OFFICIAL_RECORDS = "ISSUE_OFFICIAL_RECORDS"
    EXPORT_OFFICIAL_RECORDS = "EXPORT_OFFICIAL_RECORDS"
    VOID_OFFICIAL_RECORDS = "VOID_OFFICIAL_RECORDS"

    # Field operations
    USE_FIELD_OPERATIONS = "USE_FIELD_OPERATIONS"
    MANAGE_FIELD_OPERATIONS = "MANAGE_FIELD_OPERATIONS"
    CONFIGURE_FIELD_OPERATIONS = "CONFIGURE_FIELD_OPERATIONS"
    VIEW_FIELD_LOCATION = "VIEW_FIELD_LOCATION"

    # Data tools
    GLOBAL_SEARCH = "GLOBAL_SEARCH"
    IMPORT_EMPLOYEES = "IMPORT_EMPLOYEES"
    IMPORT_OPERATIONAL_DATA = "IMPORT_OPERATIONAL_DATA"
    EXPORT_OPERATIONAL_DATA = "EXPORT_OPERATIONAL_DATA"
    BULK_MANAGE_EMPLOYEES = "BULK_MANAGE_EMPLOYEES"
    BULK_MANAGE_TASKS = "BULK_MANAGE_TASKS"
    BULK_MANAGE_RECORDS = "BULK_MANAGE_RECORDS"

    # Finance / HR sensitive data
    VIEW_COMPENSATION = "VIEW_COMPENSATION"
    MANAGE_COMPENSATION = "MANAGE_COMPENSATION"
    VIEW_COMPENSATION_HISTORY = "VIEW_COMPENSATION_HISTORY"
    MANAGE_COMPENSATION_ACCESS = "MANAGE_COMPENSATION_ACCESS"
    EXPORT_COMPENSATION = "EXPORT_COMPENSATION"
    VIEW_FINANCIAL_REPORTS = "VIEW_FINANCIAL_REPORTS"
    VIEW_HR_CONFIDENTIAL_REQUESTS = "VIEW_HR_CONFIDENTIAL_REQUESTS"

    # Analytics
    VIEW_EXECUTIVE_DASHBOARD = "VIEW_EXECUTIVE_DASHBOARD"
    VIEW_COMPANY_ANALYTICS = "VIEW_COMPANY_ANALYTICS"

    # Subscription / tenant administration
    MANAGE_SUBSCRIPTION = "MANAGE_SUBSCRIPTION"

    # Tenant security / support
    VIEW_COMPANY_SECURITY = "VIEW_COMPANY_SECURITY"
    VIEW_COMPANY_AUDIT = "VIEW_COMPANY_AUDIT"
    VIEW_COMPANY_SESSIONS = "VIEW_COMPANY_SESSIONS"
    TERMINATE_COMPANY_SESSIONS = "TERMINATE_COMPANY_SESSIONS"
    VIEW_COMPANY_SUPPORT = "VIEW_COMPANY_SUPPORT"
    MANAGE_COMPANY_SUPPORT = "MANAGE_COMPANY_SUPPORT"
    VIEW_SENSITIVE_SUPPORT = "VIEW_SENSITIVE_SUPPORT"

    # Platform control-plane only. Never tenant assignable.
    PLATFORM_ADMIN = "PLATFORM_ADMIN"
    MANAGE_PLATFORM_COMPANIES = "MANAGE_PLATFORM_COMPANIES"
    MANAGE_PLATFORM_USERS = "MANAGE_PLATFORM_USERS"
    MANAGE_PLATFORM_SUBSCRIPTIONS = "MANAGE_PLATFORM_SUBSCRIPTIONS"
    MANAGE_PLATFORM_PLANS = "MANAGE_PLATFORM_PLANS"
    VIEW_PLATFORM_SECURITY = "VIEW_PLATFORM_SECURITY"
    VIEW_PLATFORM_HEALTH = "VIEW_PLATFORM_HEALTH"
    VIEW_PLATFORM_SUPPORT = "VIEW_PLATFORM_SUPPORT"
    MANAGE_PLATFORM_SUPPORT = "MANAGE_PLATFORM_SUPPORT"
    MANAGE_PLATFORM_SETTINGS = "MANAGE_PLATFORM_SETTINGS"

    PLATFORM_ONLY = {
        PLATFORM_ADMIN,
        MANAGE_PLATFORM_COMPANIES,
        MANAGE_PLATFORM_USERS,
        MANAGE_PLATFORM_SUBSCRIPTIONS,
        MANAGE_PLATFORM_PLANS,
        VIEW_PLATFORM_SECURITY,
        VIEW_PLATFORM_HEALTH,
        VIEW_PLATFORM_SUPPORT,
        MANAGE_PLATFORM_SUPPORT,
        MANAGE_PLATFORM_SETTINGS,
    }

    SENSITIVE = {
        VIEW_COMPENSATION,
        MANAGE_COMPENSATION,
        VIEW_COMPENSATION_HISTORY,
        MANAGE_COMPENSATION_ACCESS,
        EXPORT_COMPENSATION,
        VIEW_FINANCIAL_REPORTS,
        VIEW_HR_CONFIDENTIAL_REQUESTS,
        VIEW_FIELD_LOCATION,
        VIEW_SENSITIVE_SUPPORT,
        VIEW_COMPANY_SECURITY,
        VIEW_COMPANY_AUDIT,
        VIEW_COMPANY_SESSIONS,
        TERMINATE_COMPANY_SESSIONS,
    }

    # Safe defaults only. Sensitive capabilities are intentionally excluded.
    PRESETS = {
        "EMPLOYEE": (),
        "SUPERVISOR": (
            VIEW_ALL_REPORTS,
            REVIEW_SUBMISSIONS,
            MANAGE_TASKS,
        ),
        "BRANCH_MANAGER": (
            VIEW_ALL_EMPLOYEES,
            MANAGE_EMPLOYEES,
            VIEW_ALL_REPORTS,
            APPROVE_REPORTS,
            APPROVE_REQUESTS,
            MANAGE_PROJECTS,
            MANAGE_TASKS,
        ),
        "HR_MANAGER": (
            VIEW_ALL_EMPLOYEES,
            MANAGE_EMPLOYEES,
            IMPORT_EMPLOYEES,
            BULK_MANAGE_EMPLOYEES,
        ),
        "FINANCE_OFFICER": (
            VIEW_FINANCIAL_REPORTS,
            REVIEW_SUBMISSIONS,
        ),
        "FINANCE_MANAGER": (
            VIEW_FINANCIAL_REPORTS,
            APPROVE_REQUESTS,
            FULFILL_REQUESTS,
            REVIEW_SUBMISSIONS,
        ),
        "OPERATIONS_MANAGER": (
            VIEW_ALL_REPORTS,
            APPROVE_REPORTS,
            MANAGE_PROJECTS,
            MANAGE_TASKS,
            MANAGE_DOCUMENTS,
            USE_FIELD_OPERATIONS,
            MANAGE_FIELD_OPERATIONS,
        ),
        "EXECUTIVE": (
            VIEW_EXECUTIVE_DASHBOARD,
            VIEW_COMPANY_ANALYTICS,
            VIEW_ALL_REPORTS,
            VIEW_FINANCIAL_REPORTS,
            VIEW_COMPANY_PLANS,
            VIEW_MANAGEMENT_PLANS,
        ),
        "COMPANY_ADMINISTRATOR": (
            MANAGE_ORGANIZATION,
            MANAGE_EMPLOYEES,
            MANAGE_PROJECTS,
            MANAGE_TASKS,
            MANAGE_DOCUMENTS,
            MANAGE_COMPANY_PLANS,
            USE_FORMS,
            MANAGE_FORM_TEMPLATES,
            PUBLISH_FORM_TEMPLATES,
            MANAGE_WORKFLOWS,
            PUBLISH_WORKFLOWS,
            MANAGE_REPORTING_SCHEDULES,
            MANAGE_REQUEST_TYPES,
            CONFIGURE_FIELD_OPERATIONS,
            MANAGE_SUBSCRIPTION,
            VIEW_COMPANY_SECURITY,
            VIEW_COMPANY_AUDIT,
            VIEW_COMPANY_SESSIONS,
            TERMINATE_COMPANY_SESSIONS,
            VIEW_COMPANY_SUPPORT,
            MANAGE_COMPANY_SUPPORT,
        ),
    }

    @classmethod
    def values(cls):
        return [
            value
            for key, value in vars(cls).items()
            if key.isupper() and isinstance(value, str)
        ]

    @classmethod
    def choices(cls):
        return [
            (capability, capability.replace("_", " ").title())
            for capability in cls.values()
        ]

    @classmethod
    def is_assignable_by_company_admin(cls, capability):
        return capability in cls.values() and capability not in cls.PLATFORM_ONLY

    @classmethod
    def catalogue(cls):
        return [
            {
                "code": capability,
                "name": capability.replace("_", " ").title(),
                "description": cls.description_for(capability),
                "category": cls.category_for(capability),
                "sensitive": capability in cls.SENSITIVE,
                "assignable_by_company_admin": cls.is_assignable_by_company_admin(capability),
                "tenant_assignable": cls.is_assignable_by_company_admin(capability),
            }
            for capability in cls.values()
        ]

    @staticmethod
    def category_for(capability):
        if capability.startswith("PLATFORM_") or "PLATFORM" in capability:
            return "Platform"
        if "COMPENSATION" in capability or "FINANCIAL" in capability or "HR_CONFIDENTIAL" in capability:
            return "Finance and HR"
        if "SECURITY" in capability or "SESSION" in capability or "AUDIT" in capability:
            return "Security"
        if "SUPPORT" in capability:
            return "Support"
        if "FORM" in capability or "REPORT" in capability or "SUBMISSION" in capability or "WORKFLOW" in capability:
            return "Reporting and approvals"
        if "EMPLOYEE" in capability or "ORGANIZATION" in capability:
            return "People and organization"
        if "DOCUMENT" in capability or "RECORD" in capability:
            return "Documents and records"
        if "PROJECT" in capability or "TASK" in capability or "PLAN" in capability:
            return "Work and planning"
        if "FIELD" in capability:
            return "Field operations"
        if "IMPORT" in capability or "EXPORT" in capability or "SEARCH" in capability or "BULK" in capability:
            return "Data tools"
        if "SUBSCRIPTION" in capability or "PLAN" in capability:
            return "Subscription"
        return "Administration"

    @staticmethod
    def description_for(capability):
        return capability.replace("_", " ").capitalize() + "."
