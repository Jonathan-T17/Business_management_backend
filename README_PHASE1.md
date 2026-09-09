# SmartBiz production hardening — Phase 1: authorization foundation

This package is the first production-hardening implementation batch. It intentionally changes the security model before app-by-app refactoring.

## What changes

1. Platform superusers no longer inherit every tenant capability.
2. Tenant users can never receive platform-only capabilities, even through a malformed grant.
3. Company Administrators receive a safe configuration preset so normal company setup remains usable without granting compensation, precise location, HR-confidential or other sensitive data automatically.
4. `Authorization.can_*` becomes a compatibility facade backed by capabilities instead of broad SUPERUSER/ADMIN role bypasses.
5. `TenantService` becomes tenant-only. Platform identities get no tenant business rows from it.
6. `VisibilityService` removes platform-superuser global tenant visibility, removes broad company-admin content visibility, fixes project report visibility to require project participation, and makes task content follow project/task relationships.
7. Official-record visibility preserves source-object visibility.
8. Core permission classes are capability based and platform/tenant separated.
9. Boundary tests are added.

## Important integration rule

Platform Control Center endpoints must use dedicated platform selectors/services. Do not call `TenantService` from `/api/platform/...`.

## Next migration batch

After these files are integrated and tests pass, migrate app permissions/querysets in this order:

1. users + organizations + companies
2. security + platform_admin + support
3. projects + tasks + comments
4. reports + workflows + forms_engine + reporting_schedules + requests_app
5. documents + records_management + field_operations + planning
6. analytics_ai + data_tools + activity + notifications + subscriptions + chat

Every migrated endpoint must follow: authentication -> account/company state -> platform/tenant context -> capability -> VisibilityService -> object state/sensitivity -> entitlement -> service -> transaction -> audit -> on_commit notification.
