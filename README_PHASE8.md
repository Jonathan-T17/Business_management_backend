# SmartBiz Phase 8 — Company Setup & Self-Service Administration

Phase 8 converts `company_setup` from a convenience wizard into the tenant
configuration control plane.

## Critical corrections to the existing implementation

1. `IsCompanySetupAdmin` currently permits `SUPERUSER` and is role-based.
   Replace it with `MANAGE_COMPANY_SETUP`; platform identities receive no
   tenant setup context by default.

2. The existing onboarding serializer accepts `completed_steps`,
   `skipped_steps`, and `current_step` from the client. Treat these as
   server-managed state. The frontend may request "complete step" or "skip
   step"; the backend decides the resulting state.

3. The old health score subtracts 20 per issue regardless of severity and can
   call a company ready based only on a small checklist. Replace it with
   server-derived blocking checks + warnings.

4. Existing approval/reporting builders use `count()+1` in codes. Replace with
   UUID/sequence/collision-safe code generation before production.

5. Existing builders directly create mutable FormTemplate/WorkflowDefinition
   records. Integrate the versioning/published-immutability rules from Phase 5.

6. Role presets must never contain platform-only capabilities. Sensitive
   capabilities require explicit warnings and cannot be granted by an actor
   who lacks the authority themselves.

## Self-service surfaces

The frontend should be able to operate:
- Company Profile
- Business Template
- Branches / Departments / Teams / Positions
- Employee invitations
- Role presets and advanced capabilities
- Reporting Process Builder
- Approval Route Builder
- Request Types
- Field Activity Templates
- Document Categories
- Official Record Policies
- Notification Policies
- Security configuration
- Subscription/entitlement view
- Setup Health / Readiness
- Finish onboarding

No normal tenant setup operation should require Django Admin, shell, SQL,
direct API calls, environment changes, or developer intervention.

## Important integration note

This package contains production replacement policy/services plus copies of the
retrieved original company_setup files as `*_legacy_reference.py`. Merge the
existing configuration ViewSets into `views.py`, but make them use:
- Phase 8 capability permission
- Phase 8 capability grant policy
- Phase 5 workflow/form versioning services
- Phase 6 classification policies
- Phase 7 EntitlementService
- transactional services and authoritative audit

## Next phase

Phase 9: cross-module sensitive-data classification and policy unification.
