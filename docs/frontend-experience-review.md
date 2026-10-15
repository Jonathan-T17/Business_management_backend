# Frontend experience review and rollout

Date: September 29, 2026.

Status: design review and proposed rollout. This document does not mean that the changes below have been implemented.

## Purpose

Make SmartBiz feel like one familiar workplace across company setup, daily work, company information and analysis. Every company user enters through Overview, with content appropriate to their responsibilities and existing access. The product remains centred on company operations; projects and tasks are optional.

The connected company map is the reference for clarity: show the relationship, let the person select what matters, and reveal details in place. Use the same clarity elsewhere without forcing every screen into an organisation chart or a collection of cards.

## Review coverage

- Route inventory: 74 company-workspace page files, 16 platform-administration page files, 10 public/account-entry page files, and 2 other page files. These counts include aliases and dynamic detail routes, not 102 distinct features.
- Shared source reviewed: home routing, workspace readiness gate, desktop/mobile navigation, headers, settings layout, search, theme styles, buttons, modal, table and responsive-list components.
- Detailed source samples: Overview, Company Structure, Forms, Approvals, Employees, Documents, Official Records, Analytics, Support, reporting obligations, reporting configuration, request creation, Settings and the unused MyWork component.
- Browser review in the current company administrator session: connected company map, navigation drawer, Forms, Employees, Documents and Settings. The previous map pass checked branch details and the dashboard analytics shortcut.
- This is not a completed visual or authorization test of every route or every user type. Other identities, populated approval/reporting journeys, platform pages, public flows, and full desktop/mobile/light/dark coverage remain in the rollout checklist.
- This review does not modify application behaviour, company records, access assignments or published forms.

## Findings grounded in the current application

| Priority | Finding | Effect on the user | Proposed correction |
| --- | --- | --- | --- |
| First | Company users share `/dashboard`, but content mainly distinguishes setup administrators and analytics access. The existing MyWork component is not mounted. | Employees and managers receive mostly general links instead of their pending work. | Keep one Overview entry and build attention, recent-work and summary sections from permitted data. Do not add a task-centred dashboard by simply mounting the old component. |
| First | The administrator dashboard contains the full company map above daily operations. | As a company grows, daily work can move far below the initial screen. | Keep setup guidance first until activation; afterward place today's actions near the top and retain a compact expandable company map with a full Company Structure page. |
| First | Navigation already has groups and a page search, but contains parallel destinations such as Employee directory/Company accounts and Reports/Reports due. | People must understand the implementation's categories to choose where to go. | Organise around familiar work areas with local tabs and stable labels; keep advanced settings behind their relevant area. Preserve existing links while migrating. |
| First | The browser shows both Settings and Company Setup as top-level headings on `/settings`, with personal tabs above company configuration. | It is unclear whether the person is managing their account or the company. | Separate My account from Company settings and retain one page heading and one clear route back. Use the guided journey for mandatory setup and the same saved configuration for later maintenance. |
| First | Documents renders an empty grid with no empty message and has no query-error rendering. Official Records similarly lacks explicit loading/error/empty handling. | A blank page cannot tell the user whether there is no data, loading failed, or they should take an action. | Apply distinct loading, empty, filtered-empty, unavailable and error states with an appropriate next action. Never present a failed request as zero records. |
| First | Employee search is rendered inside EmployeeList only when the result count is greater than zero. | A search with no matches can remove the search field needed to recover. This is a source finding, not a browser-reproduced interaction in this review. | Keep search, filters and Clear filters visible outside the results container. |
| Next | Invitation progress appears above the employee directory even when no invitations need attention. | Routine employee lookup requires unnecessary scrolling. | Make Directory, Invitations and Positions clear local destinations; show a compact invitation-attention summary when relevant. |
| Next | The live Forms page displays `DAILY_REPORT`, a repeated Published status/version, and “authorized scope.” Similar technical phrases occur in other screens. | Users see internal terminology before understanding the business purpose. | Map codes to business labels, use a short purpose sentence and present version detail when it helps. For example: “Complete a form or continue a saved draft.” |
| Next | Shared visual tokens/components exist, but pages use a mixture of those components, one-off markup and global style overrides. | Spacing, headings, action placement and feedback vary between screens. | Extend the shared components and migrate page families to a small set of consistent layouts. Avoid piling more global overrides onto unrelated screens. |
| Next | The forms-to-review journey is split among Forms, settings/forms, reports and reporting schedules. | Creating a reusable form, filling it and reviewing submissions can feel disconnected. | One forms workspace with purpose-based templates, a visible draft/published library, submissions and a guided configure-preview-publish journey. Show management actions only to permitted users. |
| Next | Analytics currently summarises request and form-submission activity. | The charts do not yet answer business-value questions such as production quantities or collection totals. | Add meaningful measures from eligible form fields, explicit units/date definitions, comparison periods and authorized office filters; retain access filtering and a route to underlying records. |

## Shared design rules

1. A person should quickly understand where they are, what needs attention, what they can do next, and how to return.
2. Use a stable page heading, one short description, a prominent main action, and secondary actions in a predictable place. Use breadcrumbs for nested editors and records.
3. Use cards for choosing an area, tables/lists for comparing records, timelines for review progress, the map for structure, and charts for measures. On narrow screens, records can become concise cards with the same actions.
4. Keep the existing calm teal/navy direction, with consistent type sizes, spacing, surface treatment, icon labels and status colours in both themes. Status meaning must also appear in words.
5. A list keeps its search/filter controls when empty. Distinguish no records, no matching results and failed loading.
6. Editors clearly distinguish unsaved changes, a saved draft, a submitted item and a published company form. Retain entered values after validation errors; place errors beside the relevant fields. Never imply autosave if it is not implemented.
7. Reveal advanced options when relevant. Explain sensitive access using “what this person can do” and “which part of the company,” while enforcing the actual rules on the server.
8. Show useful completion feedback: what was saved, where it can be found, and the next action. Do not use artificial success metrics or pressure to keep using the product.
9. Keep keyboard focus visible, controls labelled, return navigation predictable, and important controls clear of mobile navigation. Check contrast, zoom, text wrapping, touch use and reduced motion.
10. Keep context/help near unfamiliar decisions. Make general support consistently discoverable; avoid presenting an inactive permission-request workflow as if a request was sent.

## Overview for every company user

These are content priorities, not roles inferred from job titles. Actual capabilities, assignments and server-filtered data determine which sections are available. A person may have several responsibilities and see the corresponding sections together.

| Working responsibility | Overview should lead with | Additional exploration |
| --- | --- | --- |
| Company setup administrator, setup unfinished | The next required setup step and saved progress | Review earlier steps and the growing company map |
| Company administrator, company active | Items needing administration, invitations needing action, relevant approvals | Company structure, forms and company settings |
| Executive with explicitly assigned company oversight | Company results, branch comparisons, exceptions and decisions | Company map and the permitted supporting records |
| Branch/department manager with supported assigned scope | Work and reporting due in their permitted area, pending decisions | Their people/structure and relevant analysis where authorized |
| Employee with an assigned position | Reports due, returned items, saved drafts, own requests and recent work | Forms, documents and other work available to them |
| Invited employee awaiting assignment | Welcome, assignment status, profile and account-security actions | Explain the next administrative step without exposing company data |

All receive a familiar visual structure. Access to Overview does not imply access to company-wide figures, employee records, compensation or the whole company map. Do not derive authority from CEO/manager titles, reporting lines or location. Department/team authority and additional analytics data must only be exposed after their backend support is verified or implemented.

## Proposed navigation

Use a compact top-level menu with local navigation inside each workspace. Exact labels can be refined during implementation:

| Workspace | Contents |
| --- | --- |
| Overview | My attention, quick actions, recent work, relevant summaries |
| Forms & reporting | Available forms, saved/submitted work, reports due; template library and schedules for permitted managers |
| Requests & approvals | My requests, decisions waiting for me, review history |
| Company & people | Company map, directory, invitations, positions and responsibilities |
| Documents & records | Working documents and final business records, clearly distinguished |
| Analytics | Activity and business measures with meaningful filters and record detail |

Notifications, messages, Help and My account stay easy to reach. Company settings remain an administrative destination; setup is prominent while it is required. Optional planning remains secondary. Mobile navigation should preserve the same concepts and use available work actions, with More for the remaining destinations.

## Rollout order and acceptance

| Stage | Work | Evidence required before calling it complete |
| --- | --- | --- |
| 1. Shared foundation | Navigation hierarchy, page/record headers, tabs, status labels, empty/error/loading states, editor actions and theme consistency | Representative list, detail and editor work on desktop and narrow screens; keyboard navigation works; no lost routes or new access grants |
| 2. Useful Overview | Common layout with setup/personal/management/oversight content, relevant pending work, recent work and compact structure exploration | Authorized representative identities tested; empty/error states truthful; displayed counts come from the correctly filtered data; unassigned users remain restricted |
| 3. Daily work | Forms, submissions, reports due, requests, approvals and their detail pages | Find an item, create/continue a draft, review, submit, return/correct and track status end to end with appropriate test records |
| 4. Company administration | Structure, people, invitations, positions, access, setup and company settings | Directory search recovers from no matches; structure and reporting remain understandable; deliberate access edits show changes before saving |
| 5. Business analysis and libraries | Form-value charts, comparison filters, documents, final records and imports/exports | Aggregations have correct units, periods and authorization; charts have a readable data alternative; library empty/error states and navigation verified |
| 6. Remaining surfaces | Support, messages, notifications, subscriptions, optional planning, account entry/recovery and platform administration | The same visual/interaction rules applied, while platform and company access stay separate |

Do not postpone basic loading/error states on a problematic daily-use page just because its full redesign belongs to a later stage. The complete rollout remains open until every route family and its relevant user journeys has evidence, including large lists, narrow layouts and permitted/denied access.

## First implementation slice

Start with navigation and shared page patterns, applying them to Overview, Forms, Employees and Settings. Fix the clear empty-state and filter-recovery issues alongside them. This gives a reviewable group of connected screens before extending the pattern throughout the route inventory. It does not require deleting company data or resetting setup.

## Route inventory

The companion inventory lists every page file at the review date. “Inventoried” does not mean visually verified, functionally tested or redesigned. Maintain evidence separately as each rollout stage is completed.

See [Frontend route inventory](frontend-route-inventory.md).

## Implementation evidence — 30 September 2026

The first slice is applied: grouped sidebar destinations, workspace breadcrumbs and local navigation, separate My account, Overview quick actions and personal reports, compact company-map exploration, Forms cards, a People directory with persistent search controls and direct invitation tracking, Company settings cards, and Documents loading/error/empty states. Existing setup gates and authorization remain in place. Positions navigation follows the page's organization-management requirement; company-map links follow its existing access requirements.

Employee directory searches previously ignored the search parameter. The backend now searches name, email and employee ID after restricting the queryset to the permitted company/branch/person. Six API tests pass, covering those fields, no matches, clearing search, tenant and branch isolation, and pagination. Twenty-four frontend helper/API checks pass. The full frontend type check passes. Targeted lint passed for the original implementation; follow-up lint status is recorded separately when available.

Live administrator observations confirmed Overview, company-map expansion, the People directory and search reset before the search fix. Browser verification resumed after the connection recovered: the invitation progress URL selects Track invitations; an unmatched directory query shows no matches and Clear search restores the person; Forms lists the prepared form and opens its entry screen; Company settings has a single main heading and grouped cards; My account has separate profile/notification/security tabs; Documents shows its empty library and add-document action. Separate invitation email fields can be added and removed, and bulk mode explains deferred position assignment. No invitations were sent and no company data was reset.

Desktop settings and invitation tracking were inspected at 1280×900; invitation tracking and form entry were inspected at 375×812, without horizontal overflow. Forms, People and Documents were also inspected in the default narrow browser. The form-entry instructions and save-failure wording now use plain language; its surface follows the shared theme instead of a fixed white panel. The follow-up full type check and targeted lint both pass. These are administrator observations in the current dark theme, not full role or theme acceptance. Personal profile still exposes internal identifiers and role codes; refining that screen remains part of the remaining-surface rollout.

This is the first implementation slice, not completion of the 102-page rollout. The next daily-work pass must reconcile existing reporting-obligation and approval API shapes with their screens before presenting accurate work counts or calling those journeys complete. Representative employee/manager access journeys and responsive visual checks remain required.

## Daily-work continuation — personal reporting

Reports due now uses the server's personal `mine` endpoint and normalizes its scalar form/schedule identifiers plus separate names. The adapter retains only fields needed by the screen. Starting a report consumes the actual `submission_id` response and opens the draft. To complete and Submitted & closed views use business-friendly statuses and distinguish Continue report from View report. The dashboard no longer counts LATE as unfinished: this backend status means submitted after the deadline.

Contract checks cover personal endpoint selection, both name shapes, removal of unused private fields and the draft-start response. Full type and targeted lint checks passed. Live administrator reporting is empty; its views were checked without creating company records. Populated journeys were subsequently checked in an isolated test database, as recorded below.

## Approval integration and populated journey checks

The workflow response now includes current step, source identifiers and permitted actions evaluated on the server against runtime participation, position currency, delegation and source visibility. The frontend normalizes submitter names, retains only needed response fields, handles completed routes with no current step and collects all visible inbox pages using the fixed API endpoint. Approval endpoints now call the existing locked runtime service and pass the request through to source finalization. Decision labels, reason input, retry and action-bar theme styling were refined.

Scheduled-report entries now change with the linked submission's approved, rejected or returned decision. Returned reports appear under To complete and can reopen the same draft and resubmit. API tests use disposable test companies, submissions and employee/manager identities; they do not modify the running company's records or accounts.

Seventeen backend tests passed across the populated journey, runtime action and reporting-job suites. They cover personal lists, cross-author start denial, repeated start returning the same draft, submission, all three decisions by employee and manager recipients, unrelated-person and cross-company denials, required reasons, duplicate decisions, disabled return/reject actions, status synchronization and return/resubmit. Approval adapter checks and targeted lint passed. The live administrator inbox was observed empty before the interruption; populated browser layouts and real employee/manager sessions remain unverified. Those require suitable signed-in test accounts, not client-side role spoofing. Delegation and confidential-source variants need additional dedicated acceptance coverage.

The interrupted development server left malformed generated route declaration and validator files. Next.js type generation succeeded; the generated files replaced the damaged development copies, adjusting the validator's relative source paths for its development directory. The final full type check passed, as did targeted lint and diff whitespace checks. This repair changes generated cache only, not application routing.

## Live admin follow-up — analytics availability

The signed-in administrator's approval inbox loads with no waiting decisions. Dashboard analytics failed because the subscription service rejects the company's current subscription as unavailable. The analytics page confirmed the active-subscription requirement; the subscription page had misleadingly shown Active using only `is_active`. Its badge now also uses the server's `is_valid`, and the live page displays Renewal needed.

Dashboard and Analytics share an availability explanation: administrators can review the company subscription, other users are directed to their company administrator, access denials are explained separately, and transient errors retain retry. The live navigation to Subscription was verified. No renewal, billing, cancellation or access grant was performed. Populated employee/manager browser journeys still require dedicated signed-in test accounts; the isolated API coverage is complete for the scenarios above.

### Live employee and branch-manager check — 1 October 2026

Inspected the three user-provided sessions: Honore DUSABAMAHORO (Employee position), Uwera Chantal (Branch / Site Manager position), and Jonathan TWIZE (company administrator). Both non-admin accounts use the EMPLOYEE account role; position permissions determine their work access. Their positions initially had no capability grants. Uwera's manager position initially used company-wide scope. Food Production's separate manager relationship remains unset; it was not included in the approved access changes.

After explicit user approval, the Employee position received USE_FORMS and SUBMIT_FORMS. The Branch / Site Manager position was restricted to its existing Food Production branch and received USE_FORMS, SUBMIT_FORMS, VIEW_FORM_SUBMISSIONS, VIEW_ALL_REPORTS, REVIEW_SUBMISSIONS and VIEW_COMPANY_ANALYTICS through the audited grant service. No confidential HR, finance, payroll or company administration grants were added. Existing holders of these positions receive the position grants.

Dashboards now show the current active position and branch from the user serializer, include My reports, and explain missing form access. Approval empty states explain assigned reviews. Fixed duplicate company branding in the header. Live employee form-library and Daily report questions were verified; manager analytics loaded; administrator setup links remain available. There are no assigned reports or pending reviews in these accounts, so browser submission/decision integration remains unverified. No real company submission or workflow was created during this check.

Validation: 13 tests passed across primary-position scope and populated reporting/approval suites; frontend type checks and targeted lint passed.

### Populated browser reporting journey — 2 October 2026

Completed the user-authorized, clearly labelled TEST journey in Business Group Ltd: Honore saved and submitted a Food Production report; Uwera requested a correction; Honore read the reviewer note, added the sample Morning shift, saved and resubmitted; Uwera inspected the locked corrected source and approved it. The second workflow instance shows Approved / Review complete with no decision buttons. Honore's Submitted & closed history shows Approved, and Uwera's dashboard shows one approved submission and zero awaiting review. The resubmission occurred after the due time and correctly appeared as Submitted late before approval.

Fixed author-only returned-report note retrieval to use the latest workflow's started_at field. The regression tests caught the initial incorrect date-field lookup before completion. Form fields now have associated labels and theme styling, save/submit feedback is explicit, and actions disable while requests are pending. Thirteen reporting/approval and primary-position scope tests pass; frontend type checking and targeted lint pass.

Manager in-app notifications arrived for the original and resubmitted reviews. The employee notification list remained empty after return and approval. Clicking the manager's review notification marked it read but did not navigate to the review. These notification gaps remain for a subsequent implementation pass. Cross-company and unrelated-user denials were verified in isolated API tests, not with additional live browser accounts. Clearly labelled TEST records are retained; official company reports were not edited.

### Review notification completion — 2 October 2026

Workflow terminal decisions now send the submitter a brief in-app outcome with an internal source link, respecting existing notification preferences and company policy. Messages omit reviewer notes and source contents; access is still checked when opening the source. No decision emails are sent. New reviewer notifications include an explicit approval URL; the frontend also recognizes numeric workflow references in older notifications without URLs.

Verified a second clearly labelled TEST submission through Honore and Uwera: return notification arrived and opened the editable source with its reviewer note; after correction/resubmission, the manager notification opened the new pending workflow; approval notification arrived and opened the approved, locked source. An older manager notification also opened its completed workflow. Dark-mode unread contrast was corrected using shared theme colours, internal event codes were replaced with Open details, and the introduction now describes work and reviews in plain language.

Twelve reporting/approval and runtime tests pass, including all terminal outcomes, no duplicate notification on repeated decisions, protected reviewer-note content and disabled in-app preferences. Final frontend type checking and targeted lint pass. The dark-mode unread row and both source links were verified in the browser. The second TEST submission is 852fe850-b876-4801-8361-c6f6ea6384cd; its returned and approved workflow instances are 3 and 4. Test records are retained for review.

### Shared dark-mode contrast review — 2 October 2026

Scanned 214 frontend UI source files for legacy colour utilities. Extended the shared theme with exact rules for pale and translucent status surfaces, muted labels, purple/violet badges, borders and hover states. Solid action-button backgrounds and white labels retain their existing treatment. Inputs now have stronger dark-mode boundaries and keyboard focus outlines use a brighter company/platform accent. The legacy utilities are shared across company, employee, manager, platform and public screens.

Visited 69 distinct routes across company setup, people, forms, reporting, requests, documents, records, analytics, notifications, account preferences, support, optional planning, all 14 platform pages and seven public account pages. Used read-only computed-style sampling and visual checks; this is representative review rather than complete accessibility certification. Loading/empty states were encountered on some routes. Gradient backgrounds, disabled controls, every populated record variant, hover interactions and permission combinations are not exhaustively measured. Populated manager charts, the employee's approved report, the company map, the platform subscription table, branch dialog and renewal dialog were inspected separately. Desktop platform subscriptions were checked at 1280×900; narrow company/employee layouts used the normal browser viewport. Temporary viewport overrides and administrator/manager theme changes were restored; the platform user's existing dark preference was retained. No operational records, invitations, subscriptions or credentials were changed in this pass.

Fixed the empty heading on untitled form submissions by falling back to the template name. Profile now shows readable company/branch names and position, with a formatted account role instead of internal IDs. Employee and administrator profiles were verified in the browser. Review evidence is saved in dark-contrast-review.json and dark-platform-subscriptions.jpg in the task's visualization directory.

### Delegated review and populated records — 2 October 2026

Rechecked completed workflow 4 and its approved TEST form through both the employee and branch-manager browser sessions. Both show Review complete with no decision controls; source answers are disabled and attachments are locked. No live records or grants were changed.

Isolated API checks exposed mismatched delegation permissions leaking workflow metadata, and valid delegates being unable to act or read the source form. Workflow visibility now matches the delegation permission to its workflow target type. Submission visibility includes the actual assigned review records, and its read permission admits current participants without granting form creation/editing rights. Existing tenant, position-currency and field-disclosure policies remain enforced.

Regression coverage includes active, expired, cancelled, future and wrong-permission delegation, delegated actor attribution and compensation-answer redaction. Thirty-two reporting, workflow, form-governance, position-scope, attachment and sensitive-boundary tests passed after the fixes. Live delegated-account browser checks are not claimed; these delegation variants were tested in an isolated database.

The final fourteen-test reporting suite also passed with additional assertions that delegates cannot edit source answers and cancellation immediately removes workflow/source access. Changed-code whitespace checks passed; an unrelated existing whitespace issue in subscriptions/models.py was left untouched.
