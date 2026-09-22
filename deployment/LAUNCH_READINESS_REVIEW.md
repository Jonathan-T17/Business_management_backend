# Paired application launch review — 2026-09-17

Scope: local backend and sibling business_management_frontend checkout. This is a
baseline code/configuration and automated-check review, not production certification.
Existing README edits and deleted historical documentation were preserved.

## Repair progress

On 2026-09-20, the company setup and operations dashboard implementation was added.
See [Company setup experience](COMPANY_SETUP_EXPERIENCE.md) for completion rules,
access enforcement, existing-company behaviour and the scope of the new charts.
The full backend suite passed 150 tests; the final setup/analytics/schema regression
selection passed 13 tests. The final frontend production build and ESLint passed,
and static contracts resolved 278 API calls and 44 capability constants.
The user successfully signed in after the local email connection investigation.

The frontend lockfile now matches the manifest, and installed Next.js is 16.3.4.
The updated frontend passed a production build, TypeScript and ESLint. The security
policy now includes both tenant and platform API origins; a configuration execution
check confirmed distinct domains are allowed while production unsafe-eval stays disabled.

Production now uses the correct Django referrer-policy setting and requires an
explicit FRONTEND_URL, also included in the example environment.

Reporting commands now use the existing company-local generation and overdue-state
services instead of missing methods. Beat queues reporting maintenance every minute.
In-app reminders use company-local mornings and final-hour deadlines, and persist
notification/flag changes atomically under row locks. Celery task discovery passed.
Seven focused tests passed for the initial repair, including existing reporting
configuration and Django/migration checks. All six reporting-job tests subsequently
passed, including linked draft/submitted overdue cases. The 277-call/44-capability
frontend contract check also passed after the repairs. No live scheduler or
application-data command was executed.

On 2026-09-19, strict API schema generation passed with zero errors and warnings.
Missing view contracts, computed-field types, enum names and operation collisions
were corrected. Schema inspection now works without database access. Four new tests
cover schema structure and actual login/OTP/dashboard/onboarding responses.
The full backend suite passed: 147 tests. The remaining pytest warnings are from
drf-spectacular's use of a deprecated Python typing API, not schema diagnostics.

Local browser checks reached the landing, login and registration pages. Login
displayed an email-delivery failure (HTTP 503); authenticated browser journeys
remain unverified. SMTP delivery must be checked in the intended runtime, since
this local backend was started under the restricted execution environment.
Registration controls and structured API-error handling were repaired after
browser/source inspection. TypeScript, ESLint and the production build passed.
The rebuilt registration page passed browser checks for all four required-field
messages, keyboard password visibility toggling, corrected explanatory text and
navigation to login. No account was created during these checks.

Remaining: deployed worker/broker verification,
clean-install verification in staging, and the end-to-end release evidence below.
The numbered findings below preserve the baseline review and its rationale;
items 1, 2, 3, 4, 6 and the referrer spelling have now been addressed in code.

## Verified locally

| Check | Result |
| --- | --- |
| Frontend/API static contracts | 277 calls, 44 capability constants; no unresolved calls or unknown capabilities |
| Django system checks | Passed |
| Migration consistency | No changes detected |
| Configured database migration plan | All listed migrations applied; no application migrations executed |
| Frontend TypeScript | Passed with incremental writes disabled |
| Frontend ESLint | Passed |
| Frontend production build | Passed on Next.js 16.3.4 after dependency and registration repairs |
| Public registration browser checks | Required-field validation, keyboard visibility control and login navigation passed |
| Backend regression suite | All 147 tests passed in 467.22 seconds |
| OpenAPI generation/validation | Passed --validate --fail-on-warn; zero schema errors/warnings |

Backend checks used Business/Scripts/python.exe (Django 6.0.2). Default Python lacks
Django. Frontend build success does not validate production API addresses or a clean install.

## Findings to address before release

1. **Frontend dependency manifest and lockfile disagree.** package.json requests
   Next.js and eslint-config-next 16.3.4; package-lock.json records 16.1.6 for both.
   The manifest also declares PostCSS ^8.5.26 without a matching root lock entry.
   Reconcile intended versions and regenerate the lockfile, then verify a clean
   installation and repeat the build. Existing node_modules can mask this mismatch.
2. **Reporting jobs are not wired into the supplied scheduler.** Compose starts
   Celery Beat, but repository search found no task definitions or beat schedule.
   Reporting obligation generation, reminders and overdue processing exist as
   management commands. Configure and verify their actual schedule, timezone,
   duplicate-run handling and failure monitoring before relying on automatic reports.
3. **Frontend security policy omits a separately hosted platform API.**
   next.config.ts derives connect-src only from NEXT_PUBLIC_API_BASE_URL, while
   src/api/client.ts also accepts NEXT_PUBLIC_PLATFORM_API_BASE_URL. When the latter
   uses a different origin, browser policy blocks those requests. Include both
   configured origins and verify platform authentication in the browser.
4. **API schema is incomplete despite a zero exit status.** Some views are omitted
   because serializers cannot be inferred; fields and operation IDs also have
   diagnostics. Add accurate schema annotations and a verification gate that treats
   diagnostics as failures. Do not treat the current generated schema as complete.
5. **Deployment infrastructure remains unverified.** The supplied Compose file has
   no HTTPS proxy, frontend service, published backend port or application health
   checks. These can be external services, but the actual deployment must provide
   them. Docker was not available on PATH for this review.
6. **Frontend URL must be explicitly supplied in production.** The example production
   environment omits FRONTEND_URL, while backend settings default to localhost:3000.
   Invitation, verification and password-reset messages use this setting. The runbook
   mentions adding it, but the deployment template should also make it explicit.

Additional configuration correction: settings_production.py assigns REFERRER_POLICY,
but Django recognizes SECURE_REFERRER_POLICY. The intended strict-origin-when-cross-origin
value therefore does not take effect through that assignment; Django's default remains.

## Remaining end-to-end release evidence

- Exercise employee, manager, company-admin and platform identities with two companies;
  verify denied cross-company access as well as successful journeys.
- Verify login, OTP, refresh rotation, logout, invitation, reset and session revocation.
- Exercise setup, forms/versioning, requests/approvals, projects/tasks, reporting,
  documents/private downloads, employee replacement, subscriptions and support.
- Verify empty/populated/error states, mobile/desktop layouts and both themes.
- Test deployed HTTPS/origins, real email, private storage, scheduled processing,
  representative load, monitoring, backup restoration and rollback on private staging.

Browser access and refresh tokens currently live in sessionStorage/localStorage;
review the production session design together with script-injection defenses.
This observation alone is not evidence of an exploitable vulnerability.

No production deployment, real email sending or application data changes were part
of this review. Automated tests use their separate test database.
