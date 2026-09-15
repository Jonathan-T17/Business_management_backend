# Frontend control inventory

This is a source-level inventory, not a claim that every screen has passed an authenticated browser test. API modules include transitive component and hook imports. Shared authentication calls are omitted.

## Implemented in this update

- Platform subscription response now includes names, usage and validity; active plans are available through the platform API.
- Plan changes require a reason, reject inactive plans and capacity violations, and save an audit record atomically.
- Subscription screen has plan changes, pagination, page search, usage indicators, and feedback.
- Shared session refresh retains rotated refresh tokens; structured API errors display field messages.
- Shared UI receives keyboard-friendly dialogs and tables, clearer focus, motion preferences, and updated styling. Company navigation includes page search.
- Django admin requires an active, non-deleted Django superuser with staff access. Platform API identity alone does not grant Django admin access.

- Company-scoped configuration routes now cover role presets, request types, field templates, document categories, official-record policies, notification policies and the capability catalogue.
- Employee grants, compensation and delegations use organization-prefixed routes and normalize paginated data. Employee-specific filtering is applied in the backend.
- Personal session/device controls are owner-scoped. Revoking a session blacklists its refresh token; existing access tokens may persist until expiry. Device trust revocation records the actor and time.
- Platform support is registered under the platform API using its existing guarded view.
- Login styling and contrast were visually checked while signed out. Authenticated portal review remains pending.

## Verification

- Frontend type check, lint, and optimized production build pass (all application routes compiled).
- Full configured pytest suite: 79 passed, one migration-state failure. After adding the no-SQL capability-choice migration, all 11 affected infrastructure and new-control tests passed. The full suite was not repeated after this metadata-only fix.
- Static route audit: 164 unique literal API calls, 25 unresolved. See FRONTEND_API_ROUTE_AUDIT.md. This is not an exhaustive contract test.
- No live application database migration has been applied.

## Boundaries and remaining work

- Keep company capabilities and platform capabilities separate. Existing capabilities and record visibility checks remain authoritative.
- Django admin model edits still need an operation-by-operation review for business-rule parity. This update restricts entry; it does not claim every admin form is a safe recovery workflow.
- Infrastructure secrets and security configuration remain deployment-managed. Strong authentication and network restriction for recovery administration remain deployment requirements.
- Plan catalog creation/editing, broader subscription lifecycle controls, and full per-screen action verification remain outstanding.
- Remaining unresolved calls include onboarding/templates, composed approval/reporting setup, analytics summary helpers, import/export and document downloads, plan lifecycle actions, request closure/cancellation, and tenant plan changes. Some may be unused helpers; audit use before implementation.
- The pytest configuration does not collect every legacy app tests.py file; the configured-suite result is not a claim that those older suites pass.
- Validate responsive layout, dark mode, keyboard interaction and success/error paths with authenticated company and platform test accounts.

## Screen inventory

| Route | API modules found in source | Verification |
|---|---|---|
| `/access-denied` | No feature API import found; inspect redirect or composition | Source mapped; live workflow pending |
| `/activity` | activityApi | Source mapped; live workflow pending |
| `/analytics/insights` | insightsApi, usersApi | Source mapped; live workflow pending |
| `/analytics` | analyticsApi, usersApi | Source mapped; live workflow pending |
| `/approvals/[workflowId]` | workflowsApi | Source mapped; live workflow pending |
| `/approvals` | workflowsApi | Source mapped; live workflow pending |
| `/branches` | branchApi, usersApi | Source mapped; live workflow pending |
| `/chat` | chatApi | Source mapped; live workflow pending |
| `/company/dashboard` | No feature API import found; inspect redirect or composition | Source mapped; live workflow pending |
| `/company` | branchApi, organizationApi, usersApi | Source mapped; live workflow pending |
| `/dashboard` | dashboardApi, subscriptionApi, usersApi | Source mapped; live workflow pending |
| `/data-tools/export` | dataToolsApi | Source mapped; live workflow pending |
| `/data-tools/import` | dataToolsApi | Source mapped; live workflow pending |
| `/departments` | branchApi, organizationApi, usersApi | Source mapped; live workflow pending |
| `/documents/[documentId]` | documentsApi | Source mapped; live workflow pending |
| `/documents/new` | documentsApi | Source mapped; live workflow pending |
| `/documents` | documentsApi | Source mapped; live workflow pending |
| `/employee/dashboard` | No feature API import found; inspect redirect or composition | Source mapped; live workflow pending |
| `/employees/[employeeId]` | capabilityGrantsApi, compensationApi, employeeDelegationsApi, employeesApi, usersApi | Source mapped; live workflow pending |
| `/employees/invite` | invitesApi, usersApi | Source mapped; live workflow pending |
| `/employees` | employeesApi, usersApi | Source mapped; live workflow pending |
| `/employees/positions` | organizationApi, usersApi | Source mapped; live workflow pending |
| `/field/[activityId]` | fieldOperationsApi | Source mapped; live workflow pending |
| `/field` | fieldOperationsApi | Source mapped; live workflow pending |
| `/forms` | formsApi | Source mapped; live workflow pending |
| `/forms/submissions/[submissionId]` | formsApi | Source mapped; live workflow pending |
| `/forms/templates/[templateId]` | formsApi | Source mapped; live workflow pending |
| `/individual/dashboard` | No feature API import found; inspect redirect or composition | Source mapped; live workflow pending |
| `/manager/dashboard` | No feature API import found; inspect redirect or composition | Source mapped; live workflow pending |
| `/notifications` | notificationsApi | Source mapped; live workflow pending |
| `/planning/[planId]` | planningApi | Source mapped; live workflow pending |
| `/planning/new` | planningApi | Source mapped; live workflow pending |
| `/planning` | planningApi, usersApi | Source mapped; live workflow pending |
| `/projects/[id]` | commentsApi, projectsApi, reportsApi, tasksApi, usersApi | Source mapped; live workflow pending |
| `/projects` | branchApi, projectsApi, usersApi | Source mapped; live workflow pending |
| `/records/[recordId]` | recordsApi | Source mapped; live workflow pending |
| `/records` | recordsApi | Source mapped; live workflow pending |
| `/reporting/obligations` | reportingSchedulesApi | Source mapped; live workflow pending |
| `/reporting/schedules` | reportingSchedulesApi, usersApi | Source mapped; live workflow pending |
| `/reports/[id]` | reportsApi | Source mapped; live workflow pending |
| `/reports/new` | projectsApi, reportsApi, tasksApi | Source mapped; live workflow pending |
| `/reports` | reportsApi, usersApi | Source mapped; live workflow pending |
| `/requests/[requestId]` | requestsApi | Source mapped; live workflow pending |
| `/requests/new` | requestsApi | Source mapped; live workflow pending |
| `/requests` | requestsApi | Source mapped; live workflow pending |
| `/settings/approval-routes` | configurationApi | Source mapped; live workflow pending |
| `/settings/company-profile` | companyApi, usersApi | Source mapped; live workflow pending |
| `/settings/documents` | configurationApi | Source mapped; live workflow pending |
| `/settings/field-operations` | configurationApi | Source mapped; live workflow pending |
| `/settings/forms/[templateId]` | formsApi | Source mapped; live workflow pending |
| `/settings/forms/new` | formsApi | Source mapped; live workflow pending |
| `/settings/forms` | formsApi | Source mapped; live workflow pending |
| `/settings/notifications` | preferencesApi | Source mapped; live workflow pending |
| `/settings/notifications/policies` | configurationApi | Source mapped; live workflow pending |
| `/settings/official-records` | configurationApi | Source mapped; live workflow pending |
| `/settings/onboarding` | companySetupApi | Source mapped; live workflow pending |
| `/settings` | companySetupApi, usersApi | Source mapped; live workflow pending |
| `/settings/profile` | usersApi | Source mapped; live workflow pending |
| `/settings/reporting` | organizationApi, reportingProcessesApi | Source mapped; live workflow pending |
| `/settings/request-types` | configurationApi | Source mapped; live workflow pending |
| `/settings/roles-permissions` | configurationApi | Source mapped; live workflow pending |
| `/settings/security` | securityApi | Source mapped; live workflow pending |
| `/settings/templates` | companySetupApi | Source mapped; live workflow pending |
| `/subscription` | subscriptionApi, usersApi | Source mapped; live workflow pending |
| `/subscription/usage` | configurationApi | Source mapped; live workflow pending |
| `/subscriptions` | subscriptionApi, usersApi | Source mapped; live workflow pending |
| `/support/[id]` | supportApi | Source mapped; live workflow pending |
| `/support/new` | supportApi | Source mapped; live workflow pending |
| `/support` | supportApi | Source mapped; live workflow pending |
| `/tasks/[id]` | commentsApi, projectsApi, tasksApi, usersApi | Source mapped; live workflow pending |
| `/tasks` | projectsApi, tasksApi, usersApi | Source mapped; live workflow pending |
| `/teams` | organizationApi, usersApi | Source mapped; live workflow pending |
| `/users` | invitesApi, usersApi | Source mapped; live workflow pending |
| `/platform/activity` | platformApi | Source mapped; live workflow pending |
| `/platform/audit` | platformApi | Source mapped; live workflow pending |
| `/platform/companies/[id]` | platformApi | Source mapped; live workflow pending |
| `/platform/companies` | platformApi | Source mapped; live workflow pending |
| `/platform/dashboard` | platformApi | Source mapped; live workflow pending |
| `/platform/failed-logins` | platformApi | Source mapped; live workflow pending |
| `/platform/health` | platformApi | Source mapped; live workflow pending |
| `/platform` | platformApi | Source mapped; live workflow pending |
| `/platform/security/login-history` | platformApi | Source mapped; live workflow pending |
| `/platform/security` | platformApi | Source mapped; live workflow pending |
| `/platform/security/sessions` | platformApi | Source mapped; live workflow pending |
| `/platform/settings` | platformApi | Source mapped; live workflow pending |
| `/platform/subscriptions` | platformApi | Source mapped; live workflow pending |
| `/platform/support` | supportApi | Source mapped; live workflow pending |
| `/platform/users` | platformApi | Source mapped; live workflow pending |
| `/change-required-password` | No feature API import found; inspect redirect or composition | Source mapped; live workflow pending |
| `/forgot-password` | No feature API import found; inspect redirect or composition | Source mapped; live workflow pending |
| `/invitations/[token]` | No feature API import found; inspect redirect or composition | Source mapped; live workflow pending |
| `/invite/[token]` | No feature API import found; inspect redirect or composition | Source mapped; live workflow pending |
| `/invite` | invitesApi, usersApi | Source mapped; live workflow pending |
| `/login` | usersApi | Source mapped; live workflow pending |
| `/register` | No feature API import found; inspect redirect or composition | Source mapped; live workflow pending |
| `/resend-verification` | No feature API import found; inspect redirect or composition | Source mapped; live workflow pending |
| `/reset-password` | No feature API import found; inspect redirect or composition | Source mapped; live workflow pending |
| `/verify-email` | No feature API import found; inspect redirect or composition | Source mapped; live workflow pending |
| `/logout` | usersApi | Source mapped; live workflow pending |
| `/` | No feature API import found; inspect redirect or composition | Source mapped; live workflow pending |
