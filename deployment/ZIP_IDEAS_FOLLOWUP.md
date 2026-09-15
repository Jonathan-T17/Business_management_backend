# Adapted ZIP ideas

## Secondary-system visibility follow-up

Adapted the secondary visibility package without applying its cumulative overlay:

- Legacy tenant AI analytics requires VIEW_COMPANY_ANALYTICS and cannot select
  another company using company_id. Its list selectors fail closed for platform identities.
- Document management requires MANAGE_DOCUMENTS; attachment access requires a tenant
  identity and retains existing parent visibility and form mutation checks.
- Ordinary record responses omit snapshot/approval_snapshot, which remain stored
  server-side. Export controls follow returned allowed_actions. PDF export requires
  a nonblank purpose of at most 255 characters; the frontend collects it explicitly.
- Generic import summaries omit the uploaded file and raw validation result. Existing
  authorized import status/error and commit flows remain available.
- Request CSV exports omit requester email and retain tenant visibility and purpose logging.

The existing central VisibilityService and explicit serializer field lists were retained.
Regression coverage is in tests/security/test_secondary_visibility_hardening.py, alongside
the existing document export, analytics and form-attachment suites. Local verification
does not constitute hosted deployment or authenticated browser verification.

## Organization/platform hardening follow-up

Adapted the organization/platform cumulative package to the current code:

- Organization permissions reject platform role identities, Django superusers and
  accounts without tenant context. Querysets independently return no tenant data
  for these identities; employee-note validation has no platform exception.
- Department/team/position mutations require MANAGE_ORGANIZATION. Employee mutations
  require MANAGE_EMPLOYEES; existing company/branch object scope remains in force.
  Capability-grant administration still requires company-administrator authority.
- Platform single-session and user-session termination use the shared revocation
  service, blacklist refresh tokens and record actor/reason. Company/user deactivation
  also supplies actor and structured reason to that service.
- Existing tenant-scoped employee IDs, their migration, explicit serializer fields,
  and the tenant dashboard identity check were retained. The obsolete platform label
  in the tenant dashboard role mapping was removed.
- The older platform sessions URL remains as a compatibility alias; both URLs use
  the same protected view and revocation service. Removing a working alias provides
  no additional authorization boundary and could break existing clients.

Regression coverage: `tests/security/test_organization_platform_hardening.py`.
This work changes local application behavior; it does not deploy the system.

The ZIP is reference material, not a replacement release. Keep the current form
authority separation, immutable versions, tenant boundaries, attachments and theme.

## Verification before release

Run `python scripts/verify_system.py` from the backend environment for the
cross-application contract checks, Django checks, migration consistency, focused
regressions, frontend type checking and linting. Use `--full` for the complete
backend test suite and frontend production build. The command stops on the first
failure and accepts `--frontend PATH` for a different frontend checkout.

The cumulative integration ZIP mostly repeats fixes already present. Its main
additional lesson is to protect the complete capability catalogue: regression tests
now check direct imported capability references (including aliases) throughout local
installed Django apps, preset membership and platform-only grant restrictions.
Dynamic lookups and arbitrary string permissions still require runtime tests.

No cumulative overlay files were applied. In particular, retain `SUBMIT_FORMS`,
`CONFIGURE_SENSITIVE_FORMS`, existing migrations, current dependencies and styling.
The ZIP's compilation/syntax checks do not establish compatibility with this system.

From the backend, using the project's Python environment:

```
python scripts/verify_frontend_contracts.py
python manage.py check
python manage.py makemigrations --check --dry-run
python -m pytest tests/contracts tests/security/test_login_flow.py tests/security/test_form_governance.py
```

From the frontend:

```
npm run typecheck
npm run lint
npm run build
```

The contract checker requires Node and the frontend's installed TypeScript package.
It parses API client aliases, HTTP methods, conditional routes and capability names.
Unknown routes/capabilities, unparsed calls and empty discovery fail the check.
Example numeric/UUID IDs cannot prove request/response shapes or authorization;
backend regression tests and authenticated smoke checks remain necessary.

## Deployment evidence still required

Record the environment, date, owner and evidence for each item before production:

- Container build and authenticated smoke test with company and platform accounts.
- Database and Redis readiness; worker queue processing and scheduled-job execution.
- HTTPS, private file access and browser security policy checks in the deployed build.
- A backup restore into an isolated environment, with measured recovery time and loss.
- A deliberately triggered monitoring alert, confirming receipt and response ownership.

These are acceptance requirements, not claims that the deployment was verified.
Follow RUNBOOK.md for deployment and rollback; do not restore over the live database
as a readiness test. Infrastructure health checks and monitoring remain deployment work.


## Operational workflows ZIP: selective integration

Applied tenant identity guards to workflow definition/runtime querysets and definition management; removed the Company Admin runtime visibility bypass. Existing recipient/delegation filtering remains. Plan items now inherit parent-plan visibility, validate tenant ownership of linked records, and cannot be moved between plans through update. Planning/request serializers reject missing tenant context. Existing planning transitions, progress, request lifecycle services, form disclosure and attachments are preserved.

Validation: 7 tests passed across operational boundaries, planning lifecycle and workflow approve/reject/return regressions. No ZIP scripts executed; no schema changes.
