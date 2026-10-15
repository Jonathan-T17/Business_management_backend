# Current staging readiness status

15 October 2026. This consolidates the implementation follow-ups to the initial 13 October system review. Earlier findings remain as historical evidence; this document distinguishes local verification from release approval.

## Decision

Local preparation is now available in [the staging guide](../deployment/STAGING.md), with a separate Compose stack, backend/frontend environment examples and an offline preflight. Eleven additional staging-preparation tests passed. Docker is unavailable locally, so container startup and host validation remain pending.

The current local application is a candidate for isolated staging validation with synthetic data. All 403 collected backend tests passed, alongside the production frontend build, full frontend lint, strict API validation and four frontend collection contract scripts. Hold public/paying-company deployment until the remaining infrastructure, historical-data and device checks are completed. A provider or server has not been selected, and local tests do not verify real infrastructure.

## Current evidence

The latest suspension wording and transition hardening passed six focused suspension/archive tests in 59.59s, frontend TypeScript/targeted lint and strict API validation. See [suspension evidence](workspace-suspension-2026-10-15.md). Live browser verification left the real company active.

Workspace archive/recovery was added after the whole-suite run below. See [its focused evidence and remaining permanent-deletion work](workspace-archive-recovery-2026-10-15.md). Four focused security tests and strict schema validation passed; automatic permanent deletion remains disabled. The previous whole-suite and frontend release build do not certify this newer change.

The permanent-deletion follow-up adds retention holds, owner-confirmed previews, protected relationship/file checks, resumable cleanup receipts and a separate deletion ledger for backup restores. Fourteen focused archive/deletion tests passed in 179.23s. The production frontend build now passes for 94 generated pages, including the receipts page; targeted lint, strict API validation and migration drift checks passed. See [its operational boundaries](workspace-permanent-deletion.md). Initial permanent deletion remains disabled until storage and backup policy are configured; whole-suite and infrastructure validation remain separate requirements.

| Area | Current status | Limit |
| --- | --- | --- |
| Company setup and people | Guided actions restored; headquarters/workplace meanings clarified; people scope/counts and access previews implemented | Representative signed-in checks; not every company structure/device combination |
| Forms and requests | Library/publication and draft/return journeys improved; request requirements, files, route selection and later result pages covered | Actual email/scanner services remain unverified |
| Configuration screens | Plan, policy, field, record and category collection loading improved; errors and draft protection added | Other optional modules and browser-history variants need broader coverage |
| Notification/document privacy | Earlier isolated privacy and tenant-boundary regressions passed | Full release regression remains outstanding |
| Record issuance | Source-aware lifecycle calls repaired; classification persisted; supported rule statuses validated | Historical classifications need review; actors still need explicit issuance authority |
| Concurrent issuance | A saved source row is locked before checking for an existing record; two separate PostgreSQL connections return the same record and allocate one number | Not a production load test or an exhaustive deadlock analysis |
| Approval/delegation | 22 workflow, record lifecycle, delegation/reporting and concurrency tests passed in the latest focused run | Repeated transitions, redacted values and denied edits covered; not every module workflow |
| Setup/dashboard regression | 14 focused setup, identity, personal-work and analytics tests passed | Not a whole-suite result; the zero-activity chart contract is now asserted with exact dates/counts |
| Frontend release build | Latest production build passed for all 92 generated pages, including TypeScript | Clean dependency installation and physical-device checks remain |
| API contract | Strict schema validation with fail-on-warning passed | Does not certify external integrations |
| Complete backend regression | 403 passed in 269.24 seconds, no failures or skips | 106 third-party drf-spectacular/Python deprecation warnings; external services are not certified |
| Frontend source and collection contracts | Full lint passed; four collection contract scripts passed | Not an exhaustive browser interaction suite |

The delegation regression assertions were aligned with the current privacy contract: inaccessible submissions return 404; edits to submitted work fail validation with 400. Tests also assert that confidential stored answers remain unchanged. No authorization rule was relaxed.

The older setup chart assertion now checks the intended 30 consecutive dates and 30 zero counts for a period without activity, rather than expecting no chart points. The regression run also identified unordered user-account pagination; tenant filtering is retained with stable primary-key ordering.

## Remaining before public deployment

1. Repeat the release build/regressions after further source changes and after a clean dependency installation in staging. The full local run is complete: 403 passed. Preserve its evidence separately from focused runs.
2. Review historical record classifications after the conservative metadata migration. Decide whether the business needs standalone GPS/photo/signature enforcement: the older flags do not enforce it, and newly enabling them is blocked. Required published-form fields are the current supported evidence path where suitable.
3. Verify representative company-admin, leader, manager, employee and platform journeys across desktop/phone, keyboard and light/dark themes, including missing setup, errors and long lists. Recheck browsers without the Navigation API for history warnings.
4. Configure isolated staging with synthetic data, private file storage, background worker/broker and actual email delivery. Run clean/infected upload checks against the real malware scanner and confirm failures remain closed.
5. Perform a real isolated database/file backup restore, confirm proxy/upload limits, health evidence, HTTPS/session configuration and deployment rollback procedures.

Staging preparation can proceed alongside remaining local checks. Public release approval requires the missing evidence rather than further cosmetic changes alone.

## Source reports

- [Original system review](system-readiness-review-2026-10-13.md)
- [Request setup](request-setup-improvements-2026-10-14.md)
- [Guided setup](guided-setup-safety-2026-10-14.md) and [locations/invitations](location-invitation-safety-2026-10-14.md)
- [Requests/Field Work lists](workspace-collection-improvements-2026-10-14.md)
- [Subscriptions/notifications](subscription-notification-improvements-2026-10-15.md)
- [Optional configuration and field-evidence limitation](optional-configuration-improvements-2026-10-15.md)
- [Official-record issuance and classification migration](official-record-issuance-improvements-2026-10-15.md)

Latest reproducible evidence: `tests/security/test_record_concurrent_issuance.py`, `tests/security/test_record_configuration_lifecycle.py`, `tests/workflows/test_runtime_actions.py`, `tests/contracts/test_approval_reporting_journeys.py`. Complete isolated results: `.review-deps/readiness-full-20261015.xml`. Focused results: `.review-deps/record-workflow-final-results.xml` and `.review-deps/setup-dashboard-stable-results.xml`.
