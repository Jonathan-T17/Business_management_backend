# SmartBiz Phase 2 — Tenant Identity & Employee Lifecycle

This package is intended to be applied after the Phase 1 Core authorization foundation.

Implemented production invariants:
- Explicit user account_state separates verification from activation/suspension/deactivation/termination.
- Tenant ADMIN no longer automatically receives Django Admin (`is_staff`).
- Platform superusers are company-less and cannot join tenant invitations.
- Tenant invitation roles are restricted to ADMIN/MANAGER/EMPLOYEE; SUPERUSER is impossible.
- Company Admin may create a backup Company Admin; last active Company Admin cannot be demoted/deactivated/terminated.
- User lifecycle mutations are centralized in `TenantUserLifecycleService` with row locking, capability checks, audit, and session revocation.
- Password reset completion revokes existing sessions and clears must-change-password state.
- OTP flow rechecks current account/company state immediately before token issuance and uses the centralized client-IP helper.
- Employee IDs are unique per company rather than globally.
- Capability-grant logic no longer treats platform SUPERUSER as implicit tenant sensitive-access administrator.
- Employee termination cancels delegations in both directions, revokes sessions, and sets account state TERMINATED.
- Pending company invites have a case-insensitive DB uniqueness constraint per company.
- Subscription limits are rechecked when invitations are accepted.
- Company deactivation/reactivation is a platform lifecycle operation; tenant admins cannot disable the whole SaaS tenant.
- Branch activation/deactivation uses a service and blocks deactivation while active users remain assigned.

## Migration required
Run Django `makemigrations users organizations companies` after integrating the model changes, inspect the generated migration, then run it in staging. The expected schema changes are:
1. `users.User.account_state` added.
2. `organizations.EmployeeProfile.employee_id` global unique removed and `(company, employee_id)` unique constraint added.
3. case-insensitive conditional unique constraint for pending `CompanyInvite` email per company.

## Integration notes
- Apply Phase 1 Core first because this phase relies on `Capabilities.MANAGE_EMPLOYEES` and the corrected `CapabilityService`.
- Platform user lifecycle endpoints in `platform_admin` should call platform lifecycle services in Phase 3; tenant endpoints in this package never manage platform accounts.
- Replace existing Users/Organizations/Companies files with the standard-name files in this package, reconcile any newer local changes, create migrations, then run the entire test suite.
