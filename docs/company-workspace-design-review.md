# Company workspace design review and proposed implementation

Date: 6 October 2026
Status: proposal for review; no application changes made in this pass.

## Purpose
A company workspace should be understandable to the company administrator, headquarters leadership, branch managers and employees without knowledge of system development. Each person should recognise their company, their position, the location they cover, the work they can perform, where saved work goes and their next action.

## Evidence and limits
Reviewed the signed-in company administrator's live dashboard, company map and requests pages, plus shared navigation, mobile navigation, dashboard access rules, setup journey, company settings, form library/management, attachments, people, reporting, approvals, documents and analytics code. Employee and manager dashboard routes already redirect to the common dashboard. This was an assessment of representative journeys and their shared foundations, not a completed visual or functional test of every route or account. Live employee, branch-manager and headquarters accounts, populated journeys, desktop/light mode and actual devices still require checks during implementation. Current company data and security permissions must be preserved.

## What is working
- A common dashboard already provides everyday action cards and adapts parts of its content to permissions.
- The company map already starts with head office and branches; location details expose departments, teams and positions.
- Setup has eight consecutive stages and preserves completed work.
- Prepared forms can be previewed, selected as company drafts, adapted and published.
- Form fields are compact and item lists support separate name, quantity and unit fields for each item.
- Shared page headers, cards, loading/error components and theme variables provide a basis for consistent design.

## Main findings
1. Navigation has nine groups and over thirty possible entries. Most groups are collapsed by default; navigating resets their expanded state. Users must repeatedly discover the same places.
2. Some pages add a second navigation row on top of the sidebar and mobile navigation. Company structure includes links to five other pages above its main content and another management-link row below it.
3. Names differ across locations: Directory / People / People directory; Analytics / Performance & charts; Company form library / Form library. Company library also blurs shared default forms and chosen company forms.
4. Daily forms, scheduled reports, general requests, materials and approval decisions have separate entry points without a single overview explaining their relationships.
5. Important actions in form administration are below the full preview. Custom creation and retirement are under More options; publication language includes Publish version and Retire version.
6. Attachments become available on an existing submission, rather than alongside receipt fields when starting a form. Users may submit before discovering upload support.
7. Some wording describes implementation: authorised scope, draft revision, internal reference and server timezone. Some concepts are legitimate but need business-language presentation.
8. The Requests page has no dedicated empty-state message or visible error recovery in its current implementation. An empty list leaves little explanation of what to do next.
9. The dashboard includes six large starting cards before personal work. Reports needing attention, company management, company map and several charts can create a long page, particularly on phones.
10. Mobile navigation currently favours the same routes for everyone. Its approval destination can be prominent even when no review work is assigned.
11. Older areas, including attachments, still use fixed white surfaces and neutral colours. Shared theme styling must be verified rather than assuming every component is consistent.

## Proposed navigation
Use six recognisable primary destinations, filtered by actual access:

| Destination | What users find |
| --- | --- |
| Home | Work needing attention, resume drafts, quick actions, relevant summary |
| Forms & reports | Company forms, saved entries, reports due; administrator-only form library and form management |
| Requests & deliveries | Track general requests and material requests; deliveries, receipts and returns |
| Reviews | Decisions assigned to the user, decision history and returned work |
| Company | Head office and branches, people, departments, teams and positions; management tools only when allowed |
| Documents | Shared documents and authorised official records |

Charts & insights is a clearly labelled destination for authorised users. Company settings belongs in a distinct management area for administrators. Notifications, Help and My account have stable, easy-to-find locations. Optional projects/tasks/planning remain secondary and do not define the company workspace.

Do not merge different record types or discard existing routes merely to simplify navigation. Group their entry points and use clearly named local views. Do not force ordinary users to search administration pages for everyday work. Keep primary destination labels visible on desktop, preserve navigation context, and use a labelled menu on smaller screens.

## One dashboard design with relevant content
The same layout and language should remain familiar across positions; work and data vary according to permissions, not job title alone.

| Person | Priority on Home |
| --- | --- |
| Employee | Reports due, returned entries, saved drafts, company forms, own requests and shared documents |
| Branch manager | Assigned reviews, permitted branch reporting/activity, branch requests and deliveries, own work |
| Headquarters leader | Assigned company decisions, permitted branch comparisons and material oversight, own work |
| Company administrator | Setup progress, people awaiting position assignment, forms awaiting publication, workspace management, own work |
| Person awaiting a position | Clear joining status, profile and help; explanation that an administrator must assign work access |

Show company name, position and covered location near the top. Put Needs your attention and Resume your work before broad exploration cards. Show a small set of useful shortcuts. Keep a compact company structure summary visible when authorised; use the Company page for the full map. Put detailed charts on Charts & insights and retain only useful summaries on Home. Distinguish no work, unavailable access and failed loading.

## Consistent page design
Every page should answer: Where am I? What is here? What can I do? What happens next?
- One title, at most one short explanatory sentence and one obvious primary action.
- Consistent search and filters beside the content they affect.
- Clear cards or tables with name, meaningful status, owner/location where authorised, date and next action.
- One predictable Back destination for details; avoid duplicated navigation strips.
- Use compact cards for exploration and a compact table when comparing many records. Do not turn every row into a tall decorative card.
- Keep essential actions visible near the relevant content. More options is appropriate for infrequent maintenance, not routine work.
- Retain every relevant form field on the open form, including optional fields. No newly introduced reveal buttons, sliders or wizard pages that conceal fields.
- Errors next to fields, clear upload progress, saved confirmation, unsaved-change protection and a visible retry for loading failures.
- Use consistent typography, spacing, controls, status colours, light/dark surfaces, readable contrast, keyboard focus and touch targets.

## Forms and saved work
Recommended administrator views: Company forms, Form library, Saved entries. Everyday workers open Company forms directly. A new company with no selected forms starts with a clear Choose forms action.

Library cards expose Preview and Add to company. The full preview remains direct and readable. Choosing creates a private company draft. Review fields, who may use it and who receives entries, then Publish form. Company forms distinguish Ready to use from Draft. Private custom forms stay company-only. Remove from company forms must preserve existing entries and show what removal means.

When filling a form, show its title, all applicable fields, separate repeatable item rows, receipt/photo upload where relevant, and Save draft / Submit. If upload needs a saved draft internally, perform and explain that coherently without forcing users to discover a separate screen. Submission must wait for successful file uploads; failed uploads must not silently disappear. Final confirmation provides View saved entry and Fill another. Saved entries show progress and authorised reviewer actions. Repeated entries of the same type remain possible on the same day.

## Company setup and responsibilities
Keep the existing dependency order: company profile; head office and branches; departments and teams; positions and reporting lines; responsibilities/access; forms; people invitations; final review.

Each step shows a short purpose, necessary fields, saved result and a clear Continue action. Optional departments/teams and later invitations must be clearly distinguished from required structure. Previously completed steps show saved information directly with Edit, rather than only a completed notice hiding those choices. Show the structure as head office above branches, then branch departments/teams and positions. A position summary should say what the person can do and where, with readable access choices and a review before changes are saved. CEO and administrator remain different responsibilities. A title must never automatically grant confidential access.

## Plain-language examples
| Current wording | Proposed wording |
| --- | --- |
| Directory | People |
| Authorised scope | Your permitted branches or company area, shown by name |
| Publish version | Publish form |
| Retire version | Remove from company forms, with history-preservation explanation |
| Draft revision | Updated draft |
| Submissions | Saved entries, with submitted status where appropriate |
| Approval routes | Who reviews this work |
| Schema / capability / internal code | Keep in background or genuinely advanced administrator settings |

Use specific examples in inputs rather than lengthy paragraphs. Do not blindly replace legal/security instructions or remove custom field guidance. Timezone explanations must reflect real date behaviour; a wording change must not falsely imply company-local dates if calculations still use a server timezone.

## Security and data boundaries
This proposal changes presentation, not authorisation. Preserve company isolation, record restrictions, attachment permissions, confidential access and server checks. Only return data the current user may access. UI visibility alone is not security. A branch-limited manager sees permitted branch information; headquarters company-wide access still depends on approved responsibilities. Avoid displaying restricted data inside counters, searches, chart tooltips or navigation previews.

## Suggested implementation order
1. Agree navigation names and destinations, then prepare representative layouts for employee Home, manager Home, Company and Forms. Review before rollout.
2. Refine shared navigation, page headers, theme styling and page patterns; keep working routes and data intact.
3. Refine Home and setup, including visible saved choices and position/location context.
4. Complete the forms journey, including upload placement, publication, saved-entry discovery and repeatable items.
5. Apply the same patterns to requests, deliveries, reviews, reporting, people, documents, charts and support.
6. Verify populated journeys across employee, branch manager, headquarters and administrator access; check light/dark, keyboard and responsive screens, then real Android/iOS before production.

## Acceptance checks
- A new user can identify their workspace, position and next action without technical explanation.
- Common destinations remain visible and use the same name everywhere.
- A worker can find a form, submit it and find the saved entry again.
- An administrator can preview, choose, adapt and publish a form without hunting for actions.
- A material request makes review, dispatch, receipt and next responsibility understandable.
- A completed setup step exposes its saved choices and a deliberate Edit action.
- Empty states explain why there is no content and offer an appropriate next step.
- No protected data or permissions are expanded by visual changes.
- Long pages, fixed navigation and dialogs do not cover controls on smaller screens.

## Open design choices for discussion
Confirm the primary names and whether Forms & reports / Requests & deliveries express the company's work clearly. Decide which three or four actions each position should prioritise on Home. Review representative screen layouts before implementing the whole workspace. Live verification of other positions is still required and is not assumed complete from administrator inspection.
## Implemented first visual pass — 6 October 2026
- Rebuilt Home with a welcoming company header, existing position/location context, central Company administration access, activity overview, compact daily-work shortcuts and company exploration cards.
- Restyled real-data request status bars, form-entry donut and dated activity line/area chart. Stable status colours, visible legends/counts and accessible exact-value table retained. Empty datasets remain empty; no invented financial or company health scores.
- Restyled metric cards and replaced standard submission labels with saved-entry wording. The summaries represent authorised operational records, not revenue or profitability.
- Primary navigation destinations now stay visible rather than requiring group expansion. Less frequent pages remain accessible through More workspace pages and search. Group expansion no longer resets on every navigation; a current secondary section opens automatically.
- Renamed shared Home, People, Reviews, Charts & insights and Company administration labels. Updated administration landing copy and moved the administrator/owner/CEO explanation there.
- Added scoped hero, shortcut, metric and chart styles for light/dark mode and reduced-motion support. Corrected a mobile flex layout problem discovered in verification.
- Live company-admin checks: Home-to-administration navigation; mobile menu and People search; chart data table with two actual dates and counts; desktop 1440px light/dark, phone 390px and tablet 768px. No horizontal overflow at measured sizes. Original dark mode restored and temporary viewport reset.
- No company records, form definitions, permissions or backend services changed. Employee/manager live checks, remaining page redesigns, integrated pre-submit receipt uploads and real-device verification remain in the broader plan.

## Implemented workspace journeys pass — 6 October 2026
- Company forms now opens selected company forms first when present, with the Form library alongside it. Administrators with no selected forms are directed to the library. Saved entries and custom creation are visible actions; removed forms remain available through the existing include-removed control.
- Form review exposes existing Fill in, Edit and Publish actions at the page header according to existing authorization. Saved-entry wording is consistent; removal still uses the recoverable retirement workflow and retains historical entries.
- Requests uses clear loading, retry, search and empty states. Request cards describe their status and offer Continue request or View progress. The current account has no request records, so populated cards were source-checked rather than live verified.
- People exposes invitation progress and a position shortcut aligned with the destination's existing organization-management permission. Reviews clearly explains when no assigned decisions are waiting.
- Completed setup steps display read-only saved choices and a deliberate Edit action. Head office is ordered before branches. Position-access summaries identify saved positions and direct the administrator to Edit for actual access choices; they do not claim to enumerate permission grants.
- TypeScript and focused ESLint checks passed, including the follow-up head-office ordering and shortcut guard changes.
- Signed-in administrator browser checks covered form cards, top-level draft actions, Saved entries with two real records, keyboard tab navigation to the library, Requests and Reviews empty states, People links, completed company profile and branch summaries, and setup next-step navigation. Desktop 1280px dark and phone 390px light/dark forms were inspected; measured forms and saved-entry views had no horizontal overflow. Original dark theme restored and viewport override reset.
- No records, permissions, tenant boundaries or backend services were changed. Employee/manager populated checks, receipt upload placement, the remaining workspace pages and real Android/iOS testing are still pending.

## Implemented daily-work pass — 6 October 2026
- Materials & deliveries now has a compact three-stage guide, a visible form-finding action, themed request cards with item previews, and proper loading/retry/empty states. The guide describes the workflow; it does not invent per-record stage completion. Quantities and permitted actions remain in the existing request detail.
- Reports due shows counts for loaded reports in To complete and Submitted & closed, uses consistent cards, and replaces question terminology with fill-in-the-fields guidance. Materials and personal-report query keys include company and user identity.
- Documents describes viewing/download access, displays permitted-document counts, readable sharing labels and categories on cards. Existing add-document capability checks remain. Employee forms now uses Saved entries consistently with the administrator view.
- TypeScript and focused ESLint passed for all four edited pages, including the follow-up compact material guide and employee label.
- Before the employee/manager tabs were closed, live checks confirmed: Uwera's manager Home with branch context and charts; Honore's employee Home without administrator controls; manager materials card opening a completed test request with approval/dispatch/receipt/return quantities and delivery history; employee forms withholding unpublished drafts while providing three saved approved entries; employee reporting showing zero outstanding and one closed report, with View report opening the approved entry; employee Documents empty state without add controls.
- Administrator checks confirmed the populated materials list at desktop 1280px dark, phone 390px light and tablet 768px light, with no measured horizontal overflow. The Documents empty state offers add controls to the administrator. Original dark theme restored and temporary viewport reset.
- No records, sharing settings or position permissions changed. Populated documents, new report submission/review actions, integrated receipt upload placement, remaining workspace pages and real Android/iOS testing remain pending. This pass verifies existing populated records through read-only navigation, not new action submissions.

## Implemented supporting-file pass — 6 October 2026
- New form entry screens now allow selecting multiple receipts, photos or supporting documents before saving/submitting. Pending files are visible with remove controls and size/type checks matching the existing server limits. Files are not uploaded merely by selecting them.
- Save/submit first saves a draft, uploads queued files sequentially, then submits only after uploads succeed. A failed upload leaves the saved draft and remaining file queue available; successfully uploaded files are removed from that queue and are not repeated on the next retry. Existing draft identity is reused.
- Saved supporting-file panels now use theme-aware styling, clear saved/empty/restricted states, named controls, retry guidance and upload/removal status. Draft submission actions are disabled while file changes are running; file changes are disabled while saving/submitting.
- TypeScript and focused ESLint passed. The upload workflow check passed for failed-upload submission blocking, retained draft identity, retry without repeating successful uploads, save-only behaviour and save-failure stopping uploads. Existing backend security tests passed: tests/security/test_form_attachments.py (2 tests), covering audience/company isolation, restricted classifications, unsupported files, upload quota and post-submit locks.
- Live administrator inspection confirmed the existing editable Daily report draft exposes receipt upload controls with Save draft/Submit form. Desktop 1280px dark and phone 390px light layouts inspected, with no measured horizontal overflow. Dark mode restored and temporary viewport reset. Screenshot saved as docs/form-supporting-files-dark.png.
- No live files were uploaded, entries submitted or templates published during inspection. The company's two current active templates are drafts, so the new first-entry file picker was code/workflow-tested rather than exercised through a live published-template submission. A published-form end-to-end upload/submission/review check remains pending.

## Implemented publication and navigation pass — 7 October 2026
- Library selections become private company drafts labelled Not available yet. Review & make available opens the form preview, then explicit publication settings. Added forms are not automatically published.
- Publishers choose Entire company, Headquarters only, or selected company branches. Ordinary publication clears old individual/position/department restrictions. Special direct-headquarters reporting authorization remains in place.
- Form availability, submitted-entry access and review routing are separate. Existing work access remains; publishers can additionally allow the selected audience to read submitted entries. Drafts, returned work and cancelled entries are excluded from this additional shared audience.
- Confidential sharing requires both publication permission and CONFIGURE_SENSITIVE_FORMS, plus explicit confirmation. The choice and audience are audited. Otherwise sensitive forms remain hidden from users lacking clearance and historical answers/files retain their restrictions. No live confidential access grants were changed.
- Delete from company forms removes all company versions from form selection and new-entry use. Historical schemas, saved entries, files and the global starter remain. Selecting the starter again creates a fresh unavailable copy. Existing archived-only selections were restored as new unavailable drafts by migration 0019; historical versions were preserved.
- Removed the include-removed control. The sidebar now exposes business sections without More workspace pages. Mobile navigation uses Menu. Publication choices and detail queries include company/user identity.
- Backend checks: 14 focused tests passed for location audiences, tenant separation, explicit confidential authority/confirmation, file sharing, draft privacy, saved-entry retention, reselection and direct-headquarters restrictions. Django system check passed and no uncreated migrations were detected. Frontend TypeScript and focused ESLint passed.
- Live administrator checks confirmed restored cards, form preview, branch selection, disabled publication with no selected branch, and disabled confidential sharing without authority. Desktop dark and phone light/dark layouts were inspected. No live form publication, deletion, file upload or entry submission was performed. Uwera's manager account refreshed successfully and showed no forms ready to complete, withholding the unpublished company drafts. The live upload/submission journey still requires a published form.
- Manager Saved entries still exposes three approved historical test entries. Publication-panel choices were cancelled after inspection, leaving live access unchanged.
- Screenshot: docs/form-publication-settings-dark.png (phone layout). Real Android/iOS device checks remain for pre-production review.

## Live form journey and upload fix — verified through 9 October 2026
- Published the existing TEST - Food Production daily report version 2 to Food Production only. Answer/file sharing remained STANDARD; no confidential sharing or new position permissions were granted.
- Honore opened the published form and filled clearly marked synthetic data. A sample receipt was selected before submission. The first upload failed because formsApi inherited the JSON request format. Submission correctly stopped and retained the same draft (b4523e9c-fca7-4392-8057-648ef86370a8).
- Corrected uploadAttachment to send multipart/form-data. After refreshing the saved draft, the sample receipt uploaded successfully. The downloaded manager copy matched the original file byte-for-byte. The same draft was submitted; it contained one saved attachment.
- Uwera received review 6 and could read the submitted answers and download the receipt. Reviewer navigation now uses Form entry, Open submitted form and Back to review. Normal entry navigation returns to Forms. Review decisions also invalidate analytics queries.
- Requested changes with an explicit test correction note. A read-only saved-record check on 9 October confirms entry RETURNED, workflow RETURNED, the note retained and one saved file. The employee correction, resubmission, manager approval and final live chart check remain pending.
- The browser automation connection still fails during sandbox startup despite the website being signed in. Local checks work only through the approved outside-sandbox fallback. No direct database changes were used to bypass the pending browser steps.
- The first-entry queued-upload path after the fix has not yet been repeated in a fresh live entry; the saved-draft upload and download path is verified. Screenshot of the submitted entry: docs/form-journey-submitted.png.
- Frontend TypeScript and focused ESLint checks passed on 9 October for the upload, review labels, return navigation and production-safe loading wrapper.

## Isolated correction-cycle verification — 9 October 2026
- Added tests/security/test_form_correction_cycle.py and ran it successfully (1 passed). The test uses separate company/users, an isolated test database and workspace temporary file storage; it does not mutate the live returned entry.
- Covers branch-only publication, employee draft and receipt upload, submission, assigned reviewer access, rejecting an empty correction note, return-note visibility, correction and resubmission of the same entry, a new review instance, final approval, retained file bytes and post-approval attachment locks.
- Verifies unrelated employees cannot approve or read the saved entry/files, and a different company cannot read the entry/files. Resubmission leaves exactly one entry and one attachment.
- Browser automation still fails at sandbox startup. Live employee correction/resubmission, manager approval, final chart verification and repeating the new-entry queued-upload path remain unverified in the browser. The live test entry remains RETURNED.


## Analytics clarity pass — 9 October 2026

Implemented horizontal status bars instead of a many-segment donut, a daily timeline with zero-activity dates, branch stacked bars on the detailed analytics page, and review waiting-time bands based on submitted_at. Dashboard charts remain compact; detailed analytics adds branch and waiting charts, 7/30/90-day presets, custom dates and branch filters. Branch options are limited to branches represented in accessible recorded work. Branch activity excludes drafts/cancellations and separates approved, awaiting review, returned and other decisions. No-branch records are explicitly named; they are not assumed to be headquarters.

All aggregates continue to use existing tenant visibility and position scope. The trend covers at most the final 30 calendar days in the selected creation-date period, including zeros. Review age is current elapsed time since submission for the records selected by creation date, not historical turnaround time. Counts are not branch performance ratings or financial results. Financial, materials and reporting punctuality metrics still need distinct data contracts, unit/currency handling and security tests before being added.

Verification: analytics scope/summary tests 2 passed; frontend TypeScript and focused ESLint passed; Django system check passed. Browser connection retried twice but the trusted Node process exited, so live visual, touch and screen-reader checks remain unverified. No live company records were changed.


## Materials analytics continuation — 9 October 2026

Kept horizontal bars for saved drafts, submitted work and decisions, with that purpose explicit in the heading. Added a Materials & deliveries bar chart to detailed analytics: awaiting review, awaiting delivery, partly fulfilled, completed, returned, rejected and cancelled material requests. Counts are requests, never a sum of unlike item units. Shared journey_status calculation with the materials workspace; completed requires approved quantities to be received net of returns. Aggregation uses the already filtered visible submissions and excludes drafts. No live company records changed.

Validation: analytics and materials workflow tests 3 passed, including inaccessible records, partial receipt, full receipt and subsequent return; TypeScript and focused ESLint passed. Live browser visual checks remain outstanding due to the previously failing browser connection. Financial and reporting-punctuality charts are not part of this pass and require separate reliable data definitions.


### Complete form-status bar chart

Replaced the form-status horizontal-only presentation with a full vertical bar chart on tablet/desktop and horizontal bars on phones. All supplied statuses appear, including zero counts, with exact values and a zero baseline. The accessible definition list retains all status values. No circular chart or backend data changes.


## Live analytics verification — 11 October 2026

Finished the resumed visual pass. Status chart now occupies its full row so desktop labels remain whole, while phone layout uses horizontal bars. Daily-chart labels use larger SVG text on phones. Verified dark-mode layouts at 1440x1000 and 390x844; restored normal viewport. Saved screenshots: analytics-status-bars-desktop.jpg and analytics-phone-review.jpg. Earlier live checks confirmed date presets, branch/material charts, manager access, and employee denial of company analytics. Manager navigation initially stalled during development compilation, then loaded after refresh.

Remaining governance finding: Jonathan sees 2 entries while Uwera sees 4. Existing visibility rules restrict administrator analytics to accessible records, so the current display is not guaranteed to cover every company entry. No permissions were expanded or live records changed during these checks. A separate review should define company-wide operational aggregation without exposing restricted answers or drafts.

Focused ESLint passed. Initial full TypeScript check failed because a generated Next.js route validator contained a duplicated trailing fragment; regenerated route types successfully and reran compilation. Financial analytics and reporting-punctuality charts remain separate future work.

Final validation outcome: Next typegen regenerated .next/types successfully but left the malformed .next/dev/types/validator.ts intact. Backed up that single cache file under .notification-fix/analytics-refresh/validator-corrupt-backup.txt, removed it, and reran the complete TypeScript check. Full-width desktop status labels and horizontal phone bars were visually verified; normal browser viewport restored. Screenshots saved with the live signed-in administrator view.


## Small-screen chart correction — 11 October 2026

Revisited the signed-in administrator dashboard after the user reported poor small-screen charts. Browser initially retained an older fixed 600-unit activity SVG and older bar layout; refreshing loaded the current ResizeObserver-based activity chart. Preserved that implementation. Changed shared Bars to put 14px labels/counts above full-width 16px bars on phones. Tablet uses horizontal comparison rows; vertical form-status bars begin at the lg breakpoint. All status counts, including zeros, remain visible. Large counts no longer occupy a fixed tiny value column.

Live dark-mode viewport checks: 320, 360, 390, 768 and 1280 pixels. Page width matched viewport at the explicitly measured 320 and 768 widths; mobile bars and desktop labels visually fit. Daily activity fills available width after refresh. Viewport override reset. Screenshot: analytics-bars-phone-improved.jpg. TypeScript and focused ESLint passed. Actual Android/iOS hardware and screen-reader testing remain outside this browser-size check. No permissions or company records changed.

## Vertical bars on every screen — 11 October 2026

Supersedes the horizontal phone/tablet presentation above following the user's preference. All shared operational bar charts now use vertical columns: form stages, request decisions, review waiting time, materials and stacked branch comparisons. Phones use numbered column labels paired with a visible list of full category names and exact counts; tablet and desktop show category names beneath the columns. Zero counts remain visible, with a common zero-based scale. Branch totals retain their decision breakdown. Daily activity remains a line chart.

Live signed-in checks at 320, 390, 768 and 1280 pixels found no page-width overflow. Visually checked phone form stages, tablet form stages and the populated branch comparison. TypeScript and focused ESLint passed. Request and waiting-time data were empty for this account, so populated examples of those two charts remain unverified in the live browser; they use the same checked component. Screenshot: analytics-vertical-phone.jpg. No access rules or company records changed.

## Named dashboards and visible daily work — 12 October 2026

Implemented Company Overview for company setup/executive authority, Branch Overview for branch managers/reviewers, and My Work for other employees. Platform heading renamed Platform Overview; its live screen was not checked in this pass. An administrator's actual assigned CEO/MD position appears alongside Company Administrator in the same dashboard; no invented position or extra privilege is assigned.

Daily work and company navigation precede charts. Added actionable authorised review previews, personal form counts and direct links to returned work, drafts and saved entries. New form-submissions/my-work endpoint intersects existing visibility with the authenticated submitter, returns metadata only, and prioritises returned work then drafts. Counts clear queryset ordering before aggregation to count repeated entries correctly. Global review navigation remains available for delegated reviewers. The dashboard's direct review shortcut uses existing review capabilities.

Verified live Jonathan/Uwera/Honore names and dashboards, Honore's 1 returned and 3 approved entries, direct Saved entries navigation, and responsive My Work at 320 and 1280 pixels without width overflow. Reused theme-aware cards and added clear position/branch badges. TypeScript and focused ESLint passed; isolated personal-dashboard API security test passed, checking authentication, capability requirement, ownership, company isolation, exact counts and bounded previews. Screenshot: my-work-dashboard-implemented.jpg. No live records or permissions changed.

Administrator analytics coverage remains limited by existing form/request visibility; labels state that only accessible records are counted. Company-wide summary policy and broader workspace-page refinements remain follow-up work. A transient live analytics connection error resolved through the visible retry button.

## Company identity and logo — 12 October 2026

Added Company logo controls to Company profile: local preview, explicit Save logo, replacement and removal. Uses the existing tenant-scoped company API and administration permissions. Shared company identity now displays a logo or initials alongside the full wrapping name on the dashboard, header and sidebar. Logos preserve their aspect ratio on a white canvas for both themes, and failed image loads fall back to initials. Company name is no longer truncated in these identity blocks. Phone header theme controls move to the existing footer to leave readable room for company identity.

Backend validates real PNG/JPEG/WebP content, maximum 2 MB and 4096 × 4096 dimensions. Frontend provides matching file guidance and initial type/size validation. Company cache invalidation refreshes branding after saving. No live logo was uploaded or removed. Five isolated tests passed, including real multipart upload/removal, employee rejection, cross-company rejection, invalid content, unsupported format, file size and image dimensions. TypeScript and focused ESLint passed after correcting preview URL cleanup. Live checks confirmed the profile upload controls, dashboard initials and readable header at 320 px without width overflow; viewport reset. Screenshot: company-logo-settings.jpg.
