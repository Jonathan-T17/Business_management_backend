# System readiness and user-experience review

Review date: 13 October 2026. Scope: local backend, sibling frontend, and the signed-in company administrator, branch manager, employee and platform owner accounts.

## Decision

**Current consolidated status (15 October): [staging readiness status](staging-readiness-status-2026-10-15.md).** The complete local backend suite passed all 403 tests. Production frontend build (92 pages), full frontend lint, strict API validation and four collection contract scripts passed. The application is a candidate for isolated staging validation; public release remains on hold for the listed device, historical-data and infrastructure evidence.

**Hold public/paying-company deployment while the remaining application and infrastructure checks are completed.** The document/upload, notification, employee-directory, workforce overview and frontend build findings have since been addressed in implementation batches. A separate staging environment with synthetic data is still needed for infrastructure verification. The findings below retain the original review evidence; use the implementation updates for current status.

Implementation updates: [documents and notifications](document-notification-improvements-2026-10-13.md), [workforce, leadership setup and complete lists](workforce-support-improvements-2026-10-13.md), [form context](form-context-improvements-2026-10-14.md), [access and filing](access-filing-improvements-2026-10-14.md), [assignment previews](assignment-preview-improvements-2026-10-14.md), [primary-position impact](primary-position-impact-improvements-2026-10-14.md), and [request setup and draft completion](request-setup-improvements-2026-10-14.md). The request batch verified 33 distinct relevant backend tests across successful focused runs, collection contracts, strict API validation, targeted lint and a production frontend build of 92 pages. Earlier batch results remain recorded in their individual reports. Remaining application work includes guided setup simplification and wider navigation, pagination, error-state and draft protection checks.

The initial review was followed by the implementation batches linked above. Browser verification has not changed live company configuration, source work or employee permissions. The later record-classification migration added metadata and conservatively restricted historical record access; content stayed unchanged. Existing test artifacts from the earlier forms journey were inspected. New security probes used an isolated test database; they did not create live documents or send emails.

## What is already working well

Official-record follow-up (15 October): [issuance reliability](official-record-issuance-improvements-2026-10-15.md) fixes report finalizer resolution, connects request approval and plan/field completion, persists record classification and aligns rule source/status choices. Five focused tests, frontend checks and migration consistency passed. Classification migration 0003 was applied locally; historical record content is unchanged but historical access is conservatively restricted. Full deployment and remaining workflow/concurrency checks are not certified.

Latest guided-setup follow-up: [setup actions and unfinished-work safety](guided-setup-safety-2026-10-14.md). Embedded creation actions are restored, department/team drafts protect setup transitions, and company profile edits have leave protection. Targeted lint, TypeScript and the signed-in team draft/discard check passed. Wider setup and infrastructure checks remain open.

Headquarters and invitation follow-up: [location and invitation safety](location-invitation-safety-2026-10-14.md). Clarified workplace identity versus headquarters designation, protected location and invitation drafts, and reset completed invitation choices. Six isolated regression tests, TypeScript, targeted lint and signed-in discard/navigation checks passed. No live invitations or location changes were made.

- Company setup has eight clear stages, saved summaries, a completion indicator, headquarters selection and optional departments/teams. Existing company configuration is preserved.
- The company map gives a useful visual hierarchy of headquarters, branches, departments, teams and positions. It distinguishes company-level positions and explains that reporting lines do not grant confidential access.
- Company, branch-manager and employee dashboards have different headings, work shortcuts, saved-entry progress and review attention. The employee can resume returned or draft work directly.
- Company administration groups setup tasks instead of showing a single unstructured settings list. Sidebar search and contextual navigation already provide a foundation to improve discoverability.
- The form library separates drafts from published forms and forms the current account can actually use. Prior live selection → publication → draft/file → submit → return → correction → approval testing passed.
- Materials show the request/review, dispatch and receipt journey together, with linked references rather than disconnected entries.
- Platform navigation separates customers, security, operations and configuration. Platform duty descriptions distinguish owner, security operator, customer support, subscription operator and auditor. Confidential company access remains separate from platform administration.
- Platform health correctly shows stale or missing evidence rather than claiming all services are healthy. Advanced administration explains password/reason requirements, and company deactivation requires a reason.

## Confirmed defects and prioritized improvements

### R1 — Document privacy and tenant-reference validation: fix first

**Priority: P1, security. Confirmed by disposable serializer probes.**

`DocumentSerializer` defines `validate` twice. The later definition overrides the earlier category-company check and category default-visibility behavior. The effective validator also does not check that the selected owner belongs to the company.

The probes showed:

| Input | Current result |
| --- | --- |
| Category belonging to another company | Accepted by validation |
| Owner belonging to another company | Accepted by validation |
| Same-company category with a PRIVATE default, visibility omitted | Private default not applied |
| BRANCH visibility with no branch | Accepted by validation |

The document model defaults visibility to COMPANY. Therefore losing a category's intended private default matters even without a cross-company read exploit. Acceptance of foreign category/owner references breaks tenant data integrity; this review does not claim to have demonstrated cross-company file download.

Merge the validators, validate every organizational/owner/category relationship, apply category defaults deliberately, and require the destination appropriate to branch/department/team visibility. Add create/update tests for these combinations before using real documents.

Evidence: `document-readiness-probes-2026-10-13.json`. Source: `documents/serializers.py`, duplicate methods at lines 331 and 399.

### R2 — The document upload page cannot complete its normal API contract

**Priority: P1, core workflow. Confirmed by source and serializer probe.**

The frontend posts the file as `file`; the API requires `initial_file`. A payload matching the page returns “No file was submitted.” The page never renders mutation errors, so the user receives no usable explanation.

The file picker also advertises `.doc` and `.xls`, which current backend content validation does not support. It omits several supported formats. Sharing options expose raw codes such as BRANCH and MANAGEMENT without explaining recipients, and the form has no branch, department, team or category selectors.

Correct the file field contract, align accepted formats and size guidance, display actionable field/server errors, and offer a clear sharing preview with the required target selectors. Keep private upload/storage checks intact. Add an actual document create/download journey in the isolated test environment.

Sources: frontend `documents/new/page.tsx`, `api/documentsApi.ts`; backend `DocumentSerializer.initial_file`, `documents/services.py`.

### R3 — Employee visibility and position-based permissions are not consistently aligned

**Priority: P1, required company/branch management flow.**

The live branch-manager account cannot open `/employees`, and the sidebar omits People. The directory UI requires employee-view/management capabilities, while the backend employee queryset still selects company, branch or self based on the account's ADMIN/MANAGER/EMPLOYEE role.

A disposable probe confirmed the inconsistency: an EMPLOYEE account with an active company-wide position and VIEW_ALL_EMPLOYEES had two profiles in its company, but the employee queryset returned only its own profile. That is inconsistent with positions and assignments being the advertised way to configure responsibilities. A company-wide position must not appear to grant a directory view that the queryset then silently reduces to the person's own profile. Branch-limited people access also needs an explicit supported policy, not a blanket company-wide grant as a workaround.

Align frontend visibility, API permissions, row filtering and count aggregation around the same tenant/branch access policy. Test company-wide leader, branch manager, ordinary employee, additional assignments, direct grants and cross-company denial.

Sources: `organizations/views.py:EmployeeProfileViewSet.get_queryset`, `organizations/permissions.py:CanViewOrganization`, frontend `utils/workspace.ts`, `core/position_scope.py:BRANCH_CAPABILITIES`.

### R4 — An administrator who is also CEO/MD needs a direct setup path

**Priority: P1 for the requested onboarding experience. Confirmed flow gap.**

Registration creates a company-administrator account but no employee profile. The current People directory contains three employee profiles, while account/company totals contain four company users. The primary/additional position assignment controls select employee profiles; the administrator is absent from those selectors.

There is an existing explanation of administrator versus CEO responsibilities, but it is collapsed under company administration and does not guide the administrator through becoming the company leader. A position's name alone grants no executive permissions, which is correct.

Add an explicit setup choice for the person who is both configurator and company leader, with a safe same-company profile/position assignment path and a preview of responsibilities. Keep confidential access separately reviewed. Do not silently give every administrator all company/private records.

Distinguish the dashboard's personal progress, operational activity visible to that account and true company-wide summaries. In the live example the company administrator's chart shows two accessible form entries, while the branch manager sees seven. This is not evidence that confidentiality should be removed; the display needs clearer scope and a deliberate leadership configuration.

Sources: `users/services.py:register_company_admin`, frontend `PositionAssignmentPanel`, `EmployeePositions`, `dashboard/page.tsx` and `settings/page.tsx`.

### R5 — People counts need a real workforce overview

**Priority: P2, before company usability trials. Confirmed UI gap.**

People currently provides search, a paginated directory count and profile cards/table. It does not provide company/branch/status filters, workforce summary cards or a headcount chart. The company map counts positions/departments/teams; these are not employee counts. The administrator dashboard has no headcount overview.

Add clearly defined counts: active employees, other employment statuses, awaiting assignment and invitation progress. Show accounts separately from employee profiles so the administrator/CEO is not mistaken for a missing employee. Include headquarters, branch and unassigned/company-level groups.

A clean horizontal bar chart by branch, with exact values and clickable branch filters, would be more useful than decoration. Keep the chart accessible with a data table and scope label. Calculate totals after permission filtering on the server; do not derive company totals from the current page of 25 profiles. Managers should see their permitted branch totals only.

### R6 — Navigation search does not understand users' task names

**Priority: P2, directly reproduced live.**

Searching the company sidebar for “permissions” returns **No matching pages**. Searching for “employees” returns only **Invite employees**, not People. The search indexes displayed labels and group names, not common task synonyms or settings destinations.

Add aliases such as employees/staff/people, permissions/access/responsibilities, CEO/leadership, approval/review and head office/headquarters. Include permitted administration destinations. Link a position's “Review responsibilities” directly to that selected position; it currently sends the user to a general page where they must choose the position again.

Preserve existing capability filtering. Search should help reach permitted tasks, never reveal hidden company content or create access.

Evidence: `system-permission-search-2026-10-13.jpg`; source `Sidebar.tsx` and `navigation.ts`.

### R7 — Position and access setup still asks users to understand too many concepts

**Priority: P2, usability.**

The user must distinguish account role, primary position, primary location/scope, additional assignments, direct grants, saved responsibility templates and confidential permissions. Existing explanations help, but they are spread across multiple pages/disclosures. The completed permissions summary lists position names without the actual scope or selected actions, requiring Edit just to inspect access.

Use one guided path: choose/create position → choose scope → choose a safe starting responsibility profile → review ordinary versus confidential actions → show who is affected → save → assign people. Keep detailed controls under an advanced section. Support a minimal small-company route without compulsory departments/teams.

Show the combined effective access, not only the selected position's permissions. Existing warnings correctly say other grants remain, but a user cannot see the complete result before changing a position. Preserve explicit confirmation for sensitive changes and last-administrator/last-platform-owner protections.

The live CEO position has four saved actions and no executive-insights action. That is existing company configuration, not a reason to automatically grant more permissions. It should be easier to notice and deliberately configure.

Implementation update (14 October): [form context clarification](form-context-improvements-2026-10-14.md) adds a visible trusted entry branch and explains descriptive work-site answers. General forms now offer permitted filing branches; targeted forms retain their current context. See [filing branches and combined saved access](access-filing-improvements-2026-10-14.md). Additional assignments now have an authorized before/after preview and review-before-save step: [assignment access preview](assignment-preview-improvements-2026-10-14.md). Primary-position and position-wide responsibility previews are now implemented and checked: [primary and position-wide access previews](primary-position-impact-improvements-2026-10-14.md). Remaining work focuses on guided setup, request-type policies, wider unfinished-work checks and staging infrastructure.

### R8 — The editable “branch or work location” field is misleading

**Priority: P2, essential wording and routing clarification. Confirmed.**

The displayed field is a TEXT answer prefilled from the branch context. Editing it describes the work site. It does **not** transfer the employee, change the structured submission branch, alter permissions or move the approval route.

The application separately stores the trusted organizational/filing branch. The backend supports permitted branch context, but the normal start-form transport posts template and answers without a branch selector. A person with more than one permitted work location needs a clear way to select the filing context when applicable; typing another branch name into the free-text answer is not that selection.

Rename the answer to **Work site / location details** or **Where was this work done?** Explain that it is a description. Display the actual **Entry branch / filed under** context separately. If multiple branch contexts are supported for the user/template, provide a selector limited to those authorized contexts and keep backend enforcement. Fixed-context forms should show that context read only.

Likewise, distinguish the editable date of work from the server's creation/submission timestamp.

Sources: `forms_engine/defaults.py`, `FormSubmissionService.create_submission/_validate_scope`, frontend `formsApi.createDraft` and start-form page.

### R9 — Registration is a useful visual reference, not a template to copy literally

**Priority: P2, shared form design and completeness.**

Registration has a focused card, comfortable spacing and one clear main action. Company dynamic forms already have visible labels, sections, automatic/prefilled indicators, attachment guidance and stronger error behavior. Registration itself relies heavily on placeholders visually, so retain persistent labels when adapting its simplicity.

Bring older setup/request/document/support/field forms onto the same shared controls: readable labels, plain-language choices, required versus optional indications, examples, limits, inline errors, a focused error summary, save/submit distinction and a clear return path. Replace unexplained codes like DAILY/BRANCH with human descriptions. Test light and dark themes and keyboard focus.

The request-type configuration page only exposes name, internal code, an amount checkbox and an optional linked form. Other meaningful policies supported by the model—such as required amounts, item quantities, attachments and sensitivity—are fixed or absent from this screen. New Request has no configured types in this company and tells even the configurator to ask a configurator, with no direct permitted setup action.

“Full fields” should mean the complete fields and policies for that business purpose, not every possible field. Review each library design for period/date, work context, relevant quantities/amount/currency, evidence, reviewer route and privacy. Preserve company adaptations and version history. Do not collect unnecessary HR or medical details merely to make a form longer.

The earlier 23-template/46-viewport checks and live correction journey remain valid evidence for their covered behavior; they do not certify every older non-library form.

### R10 — Unsaved-work protection is uneven outside the forms engine

**Priority: P2, data-entry reliability. Source-confirmed.**

Dynamic forms and the form designer have an unsaved-work guard. General setup uses `SetupEditingContext` to track changes, but `SetupJourney` applies the warning mainly to its own step links. The context itself does not install a global link/browser-close/history guard. Several standalone document/request/support/configuration forms also lack that guard.

Extend a shared guard to long setup and other data-entry forms, including sidebar navigation, browser Back/Forward, refresh and close where supported. Provide Stay, Discard and Save when saving is valid. Never auto-save permission changes or silently discard them.

### R11 — Platform support cannot identify the company reliably

**Priority: P2, customer operations. Confirmed live and in the response contract.**

The support inbox shows Company unavailable on the inspected tickets. The frontend expects `company_name`, but the support ticket serializer does not provide it. Add authorized company metadata to the platform support response and show the company, requester, reference and safe context clearly. Keep customer-only versus internal messages separated; no replies or ticket-state changes were made in this review.

### R12 — Some older modules hide errors or silently stop at one page

Optional configuration follow-up (15 October): [field templates, record rules and document categories](optional-configuration-improvements-2026-10-15.md) completes their list loading and adds visible failures and unfinished-work protection. Source review found standalone field evidence flags were not enforced by stop completion. New attempts to enable those flags are rejected, existing flags are retained with review guidance, and configuration directs companies to required published forms. This does not implement standalone GPS/photo/signature validation. Official-record source/status and end-to-end issuance semantics remain a separate follow-up.

Implementation update (15 October): [subscription and notification settings](subscription-notification-improvements-2026-10-15.md) separates failures from missing subscriptions/plans/policies, completes plan/policy paging, protects cancellation reasons and adds explicit notification-rule save/discard. Two focused backend regressions passed across successful runs, collection contracts and targeted lint passed, and the production frontend build generated all 92 pages. Signed-in checks did not change company delivery rules or cancel a subscription. Other optional configuration screens and broader state/device coverage remain open.

Implementation update (14 October): [Requests and Field Work collection improvements](workspace-collection-improvements-2026-10-14.md) adds explicit numbered paging, complete totals, request title/reference search and Field Work loading/error/empty presentation. Field Work’s heading and navigation grouping are corrected. Earlier records/support list fixes remain recorded in the workforce/support batch. Other optional modules and policy screens still need review.

**Priority: P2, operational completeness. Source-confirmed.**

Official Records has no loading, error or empty-state handling. Field Work and several subscription/notification-policy screens have incomplete error handling. A failed query can look like no work exists. Some list APIs, including records and support, extract only the first paginated result; the API default page size is 25 and the corresponding pages do not expose further pagination.

Add explicit loading, retry, access-denied and genuinely empty states, plus pagination/search where collections can grow. Do not present a failed request as an empty list. Ensure headings such as Today's Field Work correspond to actual filtering, and make missing module setup actionable for authorized configurators.

The existing company-map pagination helper is a better example: it loads all permitted pages and protects against repeated pages without importing payroll/private profile fields.

### R13 — Private report titles can appear in unauthorized project-member notifications

**Priority: P1, security. Confirmed by an isolated notification probe.**

The backend definition scan found duplicate `_notify_report_submitted` and `_notify_comment` methods in reports/views.py. Earlier behavior is overridden silently. The active submission helper notifies project members and includes a report title without an explicit per-recipient report-visibility check.

The focused probe created a PRIVATE, DRAFT report and a project member who could not view that report. Calling the active notification helper created an in-app notification for that member containing the private report title. The helper is called by report creation. No emails or live notifications were sent. Evidence: `access-notification-readiness-probes-2026-10-13.json`.

Remove dead duplicate methods and make notification recipients/content consistent with target visibility. Verify that private draft/report titles are not exposed through in-app notifications to people who cannot open the report. Notification delivery and report access must agree; do not assume an inaccessible target link makes its message harmless.

### R14 — Infrastructure and clean frontend release checks remain open

**Priority: release blockers for public production.**

The live platform health page shows stale email/reporting/private-storage evidence dated 3 October, and no completed backup evidence. The malware scanner is prepared in deployment files but has not run against a real daemon here. There is no hosting/staging server or real-phone verification yet.

The normal frontend type check failed twice at `.next/dev/types/routes.d.ts:59` with a generated-file syntax error. The inspected file contains a complete declaration followed by an invalid appended route fragment. Full source ESLint passed. This is a generated development artifact failure, not proof of an application-source type defect; a clean generation/build/type-check run is required before release. Do not edit the generated declaration manually or treat the lint pass as a successful production build.

Verify worker/broker operation, actual email/storage probes, clean/infected scanner checks, an isolated backup restore, request/proxy limits, clean dependency installation, and physical-device interaction in staging. These are separate from the locally passing unit tests.

## Verification results and limits

| Check | Result |
| --- | --- |
| Company setup, headquarters, positions, invitations, dashboards, platform, health, backup and session selection | Initial run: 61 passed, 3 failed out of 64 |
| Backup/analytics retest with backup temporary files outside checkout | 9 passed; backup path failures resolved in the test environment |
| Original chart assertion | Resolved 15 October: asserts the exact 30-day date window and zero counts for an empty period; focused setup/analytics regression passed |
| Document validation probes | Reproduced the defects above; no documents saved |
| Employee access / private-notification probe | Confirmed the directory scope inconsistency and private draft-title exposure in disposable in-app notifications |
| Python class-definition scan | 643 files parsed, no syntax errors; three duplicate methods identified |
| Frontend route/capability scan | 298 calls, 46 capabilities; no unresolved routes or unknown capabilities |
| Computed company-structure call | All five actual GET destinations manually resolved; the scanner marks computed calls for review by design |
| Django system checks | Passed |
| Model consistency and migration plan | No missing model migrations; no pending migration operations |
| Strict OpenAPI generation/validation | Passed, including fail-on-warning mode |
| Full frontend source ESLint | Passed |
| Normal frontend TypeScript | Failed in the generated development route declaration; repeated and inspected |
| Production build / real infrastructure / physical phone | Not certified by this review |

The initial backup failures arose because the test folder was inside the checkout, which the backup commands correctly prohibit. The test rerun used a separate writable location. Passing archive tests is not evidence that a real production database has been backed up or restored.

## Coverage

107 frontend page files were inventoried. Browser inspections covered the company administrator dashboard, manager/employee dashboards, People/profile/assignment, completed setup and access editor, position creation, company map, navigation search, registration reference, company forms, employee form entry, materials, reporting creation, request entry and request-type setup, document entry, support entry, and platform dashboard/health/navigation/access/companies/company detail/security/advanced administration/settings/support.

Projects/tasks, official records, field work, subscription screens, notifications/chat, data import, role policy, registration/service behavior and API clients also received code review. Later platform subscription/users navigation did not settle reliably in the local browser; those are source-reviewed/inconclusive live checks, not passes. This is not an exhaustive test of every data/state combination or a security certification.

## Implementation order

1. Repair document tenant/privacy validation and the document upload contract. Add create/update/download and per-recipient notification privacy tests. Repair any confirmed notification exposure.
2. Align employee directory access with the advertised position/scope policy. Add a safe administrator-plus-leader setup path. Show effective access before assignments.
3. Build the People overview, branch/status filters and correctly scoped headcount cards/chart. Separate employee and account counts.
4. Improve navigation aliases and direct task links; simplify position/access setup and saved summaries. Preserve explicit confidential-access review.
5. Standardize remaining forms and module empty/error/pagination behavior. Separate work-site answers from organizational filing context. Extend unsaved-work protection.
6. Reconcile the chart regression with the current contract, obtain clean frontend build/type results, rerun targeted and complete regression suites, then perform infrastructure/phone checks in isolated staging.

## Evidence files

- document-readiness-probes-2026-10-13.json
- access-notification-readiness-probes-2026-10-13.json
- system-python-definition-review-2026-10-13.json
- system-contract-review-2026-10-13.md
- system-review-browser-evidence-2026-10-13.json
- system-register-reference-2026-10-13.jpg
- system-company-map-2026-10-13.jpg
- system-permission-search-2026-10-13.jpg
- Earlier forms journey: forms-end-to-end-2026-10-12.md
- Upload infrastructure checks: forms-upload-release-checks-2026-10-12.md





