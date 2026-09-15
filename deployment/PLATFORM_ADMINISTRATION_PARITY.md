# Frontend administration coverage

The platform frontend now includes `/platform/administration`. Django admin remains
available as the recovery interface. This is an initial expansion, not complete
parity with every registered Django admin model or action.

## New configuration workflows

| Resource | Frontend operations |
| --- | --- |
| Companies | Create and edit profile, locale, contact and email presentation settings |
| Branches | Create and edit branches and managers |
| User profiles | Edit profile and tenant role; last company administrator cannot be demoted |
| Projects | Create and edit configuration |
| Project memberships | Create and edit project access |
| Plans | Create and edit prices, limits, availability and feature flags |
| Subscriptions | Create and edit company subscription, plan, status and expiry |
| Form templates | Create and edit draft configuration |
| Form fields | Create and edit fields belonging to draft templates |

Existing company activation, user lifecycle, session revocation, login protection,
audit, subscription and support screens remain accessible through platform navigation.

## Backend boundary

- The advanced endpoints require an active, non-deleted staff superuser who has
  completed any required password change. A tenant administrator or a role-only
  SUPERUSER does not inherit recovery-level access.
- Every write verifies the acting user's current password and a nonblank reason.
  Write requests are throttled to ten per minute per user.
- Models and fields are explicitly listed. Newly registered models or new fields
  do not become remotely writable automatically.
- Model forms enforce field, model and uniqueness validation. Related records must
  belong to the same company; existing company ownership cannot be transferred.
- Writes are transactional and include an optimistic version check to prevent a
  stale form from overwriting another administrator's edit.
- Each successful mutation records actor, target, reason and changed field names.
  Passwords and field values are not copied into audit metadata.
- Role changes revoke the affected user's refresh sessions. Existing access-token
  expiry behavior remains unchanged.
- Plan capacity checks reject limits below current usage. Published and archived
  form definitions cannot be edited through this workspace.

## Outstanding parity work

- Platform-account provisioning and privilege changes: implementation was paused
  after automated approval review rejected the privileged-account frontend change.
  The partially added endpoint was removed; no new account was created.
- New tenant-user provisioning, invitation management and Django auth-group editing.
- File uploads, form publication/version workflows and submission administration.
- Record deletion with dependency previews and lifecycle-specific safeguards.
- Security evidence and raw token records are not generic editable resources.
  Their operational controls should remain explicit security actions.
- Authenticated visual review of the new screen is still required.

No database migration is required for this expansion. It does not create or modify
live business records until an authorized administrator submits a form.

## Workflow integration follow-up

- Subscription capacity validation is shared by the platform plan-change service
  and advanced administration. User seats include non-deleted users and pending
  invitations; projects and branches count active records.
- Both subscription forms preview capacity problems before saving. Server-side
  validation remains authoritative when usage changes after loading the form.
- Company onboarding now uses the canonical status, complete, skip and finish
  endpoints and backend step definitions. Required steps cannot be skipped;
  malformed inputs are rejected; finishing still requires readiness checks.
- Active business templates can be listed and applied through guarded endpoints.
  Supported sections are departments, positions and document categories; applying
  twice preserves existing records rather than duplicating them.
- Refreshed static audit: 163 literal calls, 21 requiring review. This is not full
  payload-contract validation and does not cover all inline/computed API calls.
- Authenticated browser verification and the other parity gaps above remain open.

### Approval configuration follow-up

- Registered tenant-scoped approval route list, detail, create, update and preview.
- Nested reviewer inputs validate active company positions and users; platform
  recipients and cross-company reviewer assignments are rejected.
- Route/workflow activation stays synchronized. Step replacement is rejected after
  a workflow has approval history. Duplicate-name failures roll back the workflow.
- Frontend uses position names, validation feedback and activate/deactivate actions.
  Preview validates configuration; it does not promise a currently resolvable reviewer.
- Static audit now reports 17 calls requiring review, down from 21. Reporting
  process composition is still outstanding and was not enabled using legacy code.

### Reporting configuration follow-up

- Registered tenant-scoped reporting process list, detail, creation and updates.
- Creation validates company positions, reporting frequency and date fields, unique
  form field keys and approval recipients, then creates the draft form, inactive
  schedule and optional approval workflow in one transaction.
- Activation requires a published active form. Process and schedule activation are
  synchronized. The schedule starts on the company's local date.
- The frontend supplies a summary field, weekday/month-day controls, draft-state
  explanation, form-review link, activation controls and error feedback.
- No automatic notification-delivery promise is shown. Existing reporting execution
  and form publication remain separate operations.
- Tested tenant boundaries, draft activation rejection, schedule updates, duplicate
  rejection and complete rollback on audit failure. Authenticated browser review
  remains outstanding. Static audit now has 14 calls requiring review.

### Download and export follow-up

- Added the missing document download action. It applies visibility and sensitive
  document checks, serves only the recorded current version, records a download
  audit event and disables response caching. Missing versions/files return 404.
- Fixed document-version storage paths to obtain the company from the parent
  document; the version model has no company_id field.
- Connected request CSV exports to the existing endpoint and persisted the required
  export purpose. Export capability remains separate from company-admin status.
- Removed unavailable task/report choices from the export screen; these are not
  implemented by adding permissive generic exporters.
- Employee import job IDs, status contracts and commit behavior still need review.
- Static route audit now reports 12 calls requiring review. Authenticated browser
  verification remains outstanding.

### Employee import follow-up

- Connected upload, status and commit to the same employee-import routes and response shape.
- The screen displays row errors and counts, requires confirmation, and prevents repeat commits after completion.
- Imports validate email, columns, employment type, duplicate accounts/IDs and pending invitations; uploads are limited to 10 MB and 2,000 rows.
- Commit checks tenant capability, revalidates against current data, locks the job/company, enforces subscription capacity and records an audit event in one transaction.
- Imported accounts are inactive employees with unusable passwords. Invitation registration can claim only eligible placeholders recorded in completed employee imports. Existing ordinary accounts remain protected.
- Seat accounting avoids counting an imported account and its pending invitation twice. Invitation acceptance works at the exact plan limit.
- No live imports or invitation emails were sent. Authenticated visual review remains outstanding.
- Frontend TypeScript and targeted ESLint passed. Import, frontend-control, login and platform-maintenance regression suite passed (29 tests); final import-specific checks are rerun after the last validation changes.
- Static route audit: 163 literal calls, 10 unresolved. This is not a complete runtime screen audit.

### Planning lifecycle follow-up

- Added activate, complete, cancel and archive endpoints using the existing locked, audited PlanningService transition rules.
- Company-plan reads now use PlanningAccessService visibility rules; platform identities cannot browse tenant plans through these tenant endpoints.
- Responses include permission-aware allowed actions, item counts, completion percentage and blocked/overdue item counts.
- Direct status changes through ordinary create/update payloads are rejected; cross-company owners and invalid partial date changes are rejected.
- The detail screen now displays action errors and the backend target_value field, and sorts a copy of cached items.
- API regression passed: lifecycle order, repeated transitions, direct-edit bypass, foreign owner, dates, reader permissions, tenant isolation, platform isolation, progress and audit events.
- Frontend TypeScript and targeted ESLint passed. Static route audit now reports 6 unresolved literal calls (from 10). Authenticated visual checks remain outstanding.
- Plan-item editing and the remaining analytics/request/subscription route gaps require separate follow-up.

### Request lifecycle follow-up

- Added cancellation for requester-owned drafts/returned requests and closure for fulfilled requests by users with FULFILL_REQUESTS. Submitted/in-review requests cannot bypass workflow decisions through cancellation.
- Exposed allowed_actions from the same backend permission/state rules. Cancellation requires a reason, with reason/note limits of 1,000 characters.
- Cancellation, fulfillment and closure record audit events transactionally. Fulfillment uses its own capability instead of additionally requiring approval permission.
- Corrected the existing broken official-record finalizer import/call in fulfillment; configured record policies and issuance permissions still apply.
- Frontend now renders action errors, limits note lengths, uses requester_name and unwraps the submit response correctly.
- Request lifecycle API regression, frontend TypeScript and targeted ESLint passed. No live business requests were changed.
- Static audit: 163 literal calls, 4 unresolved (three analytics routes and tenant change-plan). Authenticated visual checks remain outstanding.

### Analytics overview follow-up

- Added the missing overview endpoint for tenant users with VIEW_COMPANY_ANALYTICS or VIEW_EXECUTIVE_DASHBOARD and an active subscription. Platform identities are rejected by this tenant endpoint.
- Counts use existing task/project/request visibility querysets before aggregation. Analytics permission does not grant access to hidden operational records.
- Returns active-task totals, completed/overdue task counts, active-project totals and request-status counts. No fabricated project lifecycle or reporting-compliance totals are returned.
- Supports validated inclusive creation-date filters and company branch filters. Department/unknown filters are explicitly rejected rather than silently ignored. Branch filtering follows project branch assignments for tasks/projects.
- The frontend explains the scope and provides a refresh button with loading feedback.
- API scope/filter/subscription regression, frontend TypeScript and targeted ESLint passed. Authenticated visual checks remain outstanding.
- Static route audit: 163 literal calls, 3 unresolved. Trend/compliance client methods have no current screen callers. Tenant change-plan still needs reconciliation with the platform-only subscription lifecycle service; existing generic tenant subscription writes also require review.

### Tenant subscription follow-up

- Tenant subscription routes now allow reads and explicit cancellation only. Generic create/update/delete and plan-catalog writes are disabled; platform controls remain on the platform endpoints and Django admin remains available.
- This closes generic-write bypasses around the existing platform-only plan-change service, including direct expiry and price edits. Platform identities use platform routes instead of tenant subscription routes.
- Company administrators can cancel their own active subscription with a required reason (up to 1,000 characters). The operation locks the subscription, rejects repeats, audits the reason and returns the full serialized result with allowed_actions.
- Fixed current-subscription frontend parsing (the endpoint returns a list). Removed the unavailable tenant change-plan call and obsolete plan-selection buttons. The page identifies platform administration as the place for plan changes/reactivation and displays API errors.
- Tenant subscription and existing frontend-control regressions passed: 10 tests. Frontend TypeScript and targeted ESLint passed. No live subscriptions were changed.
- Static route audit: 162 literal calls, 2 unresolved (unused analytics trend/compliance methods). Authenticated visual verification and broader payload/permission reviews remain outstanding.

### Analytics filter and route-audit cleanup

- Removed unused analytics trend/reporting-compliance client methods that referenced nonexistent endpoints. No trend or compliance calculation is represented as implemented.
- Added explicit creation-date controls to the overview: inclusive from/to dates, apply, clear, refresh, applied-range label and validation/error feedback. Removed unsupported department filtering from the client contract.
- API date-boundary regression passed, including same-day inclusion and exclusion outside the range. Frontend TypeScript passed; targeted lint result is checked before completion.
- Static audit now resolves all 160 remaining literal calls (0 unresolved). This checks URL/method existence only, excludes computed calls, and is not evidence that all payloads, permissions, workflows or screens are verified.
- Next work should broaden runtime contract coverage and authenticated screen checks; plan-item editing and other previously noted workflow limitations remain outstanding.

### Company-owned dynamic forms (September 12, 2026)

- Company capabilities separate template design, publication, submission, submission visibility/review, and sensitive-form configuration. USE_FORMS remains a compatibility permission for submission. Builder authority alone does not expose employee answers. Template audiences support company role and organizational scope; backend checks remain authoritative.
- Company users can start from a platform starter, copy a company form, or build from scratch. Published/used forms produce new draft revisions when edited. Submitted and draft answers retain their original schema snapshot and version. Publication retires the previous version; source configurations explicitly select which published version to use for new work.
- Added company builder navigation, field ordering, choices, conditional questions, sensitive classifications, audience and workflow settings, draft/preview/publish/retire/copy controls, and structured location inputs. Drafts can be saved before required answers are complete. Restricted answers remain masked and are preserved during updates.
- Request types and field-operation configurations can select published forms. Requests pin answers to their own lifecycle and permit authors to correct draft/returned answers on the request page. Field workers can open a configured form from their assigned stop; completion requires its submission or approval. Reporting continues through its existing obligation integration; fixed the workflow submission state-service reference.
- Platform maintenance exposes starter designs instead of tenant templates/fields. Tenant form access in Django admin follows company capabilities and immutable-version rules. Starter administration remains available to platform administrators. Existing business data is not copied into platform starters.
- Applied forms_engine 0003-0005, organizations 0009-0010, and requests_app 0003-0004 locally. Migration consistency check reported no missing migrations.
- Verification: 17 backend tests passed across form governance, module integration, requests, reporting, platform maintenance and sensitive boundaries. The expanded governance suite then passed 3 tests including conditional required questions and masked-answer preservation. Frontend TypeScript and targeted ESLint passed. Django system check passed.
- Browser review remains pending: the frontend on 127.0.0.1:3000 refused the connection. No claim is made that every authenticated screen has been visually verified. Attachment widgets, broader field-validation editors, and fine-grained per-form/person grants are not included in this implementation; audience roles/scopes and capabilities are the implemented authorization model.

### Forms completion: attachments and named submitters (September 12, 2026)

- Added versioned audience_user_ids and a named-person selector to the company form builder. An empty selection preserves role/scope eligibility; a selection restricts it further. It never grants submission capability, bypasses organizational scope, or grants access to other people's answers. Only active users of the same company can be configured; published revisions remain immutable.
- Added authenticated form attachment list/upload/download/removal endpoints and a reusable frontend panel on submissions and authorized request forms. File reads inherit submission visibility and require clearance for every classification in the schema. Files are delivered as downloads; form attachment serializers do not expose raw storage URLs.
- Only the author with submission authority may add/remove files while the form and any attached request are draft/returned. Submission locks serialize file changes against submission transitions. Removed attachments are deactivated. Generic attachment endpoints use the same form-specific access and lifecycle checks.
- Uploads reuse supported file types, the 25 MB limit, and subscription storage checks. Request form attachments count toward request attachment requirements, and request types that disallow attachments block uploads through the form. Changes are audited through the form endpoints.
- Applied forms_engine 0006 locally. The main regression suite passed 19 tests across form governance, attachments, module integration, reporting, platform maintenance, and sensitive boundaries. TypeScript and targeted lint checks passed; final request/download regressions are recorded below after completion.
- This completes the previously noted attachment and named-submitter work. The earlier visual-review limitation remains: authenticated visual review was deliberately omitted at the user's request. Company submission viewing/approval still follows its separate capability and workflow-participation rules.
- Final request/download compatibility checks passed: 4 tests. Frontend TypeScript and final attachment lint checks passed. Draft file removal remains available when a request configuration disallows further uploads, so authors can correct their draft.
- Final attachment and module regression rerun passed: 3 tests, including upload restrictions, draft removal, sensitive-file denial, quota denial, and request attachment requirements.
