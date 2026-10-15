# Forms review — 12 October 2026

## Assessment and evidence

The library → company draft → published form → saved entry architecture is a useful foundation. It is not yet sufficient evidence that the forms are ready for company use. The highest priorities are authoritative answer validation, predictable publication access, protection of unfinished work, and clearer company-form states.

This review inspected the current backend and sibling frontend source, all 23 designs in `forms_engine/starters.py`, catalogue update/version services, company setup, library, designer, publication, entry pages, attachment policies, and existing regression tests. Existing working-tree changes were preserved. This is a review; no form configuration, company publication, permissions, or business entries were changed.

The authenticated follow-up below supersedes the initial browser-access limitation. Initial verification context:

- The source catalogue contains 23 designs with 6–10 fields each. Runtime library records may differ because migrations preserve operator changes. Individual companies may also have customized or older versions. Their actual saved configurations were not inspected in an authenticated session.
- Opening `http://localhost:3000/forms` redirected to sign-in. Current authenticated library/company/entry screens were therefore not visually verified.
- The historical `docs/theme-aware-form-library.png` was inspected. It shows an older inline preview; the current code uses a dedicated preview. It cannot prove the current layout. `docs/forms-device-review.md` records earlier viewport checks, not current real-device certification.
- The first focused security run could not access PostgreSQL from the sandbox. With outside-sandbox database access, the 24-test run reported 3 passed, 9 failed and 12 errors. A focused first-failure diagnosis found missing `webauthn` in the selected Python environment while importing URL routes. These results do not establish nine functional form defects; the suite must be rerun in the configured dependency environment.
- The frontend-controls run reported 5 passed, 1 failed and 3 errors. The frontend contract script also stopped at the missing `webauthn` import. Frontend TypeScript checking completed successfully with incremental file writing disabled; no build or lint result is claimed.
- All 23 source designs (184 field definitions) passed `FormFieldSerializer` schema validation. The five scalar financial amount/total fields have no configured minimum. Schema validation does not establish answer validity or correct business rules.
- Direct database-independent probes of the shared answer validator reproduced the invalid-value acceptance described below.

## Prioritized findings

### 1. High: the server accepts invalid typed answers

Evidence: `forms_engine/services.py`, `FormSubmissionService._validate_field`.

Direct calls accepted DATE `not-a-date`, EMAIL `not-an-email`, INTEGER numeric `1.9`, and DECIMAL strings `Infinity` and `NaN` with empty validation rules. Date/time checks only require strings; email checks only require text; integer conversion truncates numeric fractions; decimal conversion does not require finite values. With configured bounds, NaN comparisons can also raise unexpected exceptions rather than a useful validation error.

Impact: malformed answers can enter records through API clients despite browser input types, reducing reporting reliability and potentially disrupting downstream calculations. This is a data-integrity defect, not evidence of cross-company disclosure.

Required change: parse actual ISO dates/times, validate email formats, reject fractional whole numbers and non-finite numbers, and return stable field-level errors. Explicitly decide timezone handling for DATETIME. Keep incomplete draft support while rejecting nonempty invalid values. Test both normal API updates and submission, including direct API requests.

### 2. High: publication broadens ordinary restrictions

Evidence: `FormPublication.tsx` starts with Entire company; `FormTemplateVersionService.publish` clears branch/department/team and ordinary role/person/position restrictions when publication settings are supplied. Direct headquarters routes preserve their person/position exception. The UI explains replacement in a small paragraph, but does not show the current audience or the concrete change.

Impact: an administrator can carefully restrict a draft in the designer and then publish it company-wide without an explicit before/after audience review. Revisions also open a new publication panel with generic defaults rather than the saved audience.

Required change: initialize publication from the draft's existing policy; show current and proposed submission audience, entry visibility, confidential-answer/file sharing, and review route together. Make removal of saved restrictions conspicuous and deliberate. Preserve the backend's separate confidential-sharing authority, explicit confirmation, and audit logging. If location-only publication is the intended product rule, remove misleading ordinary access controls from the designer or explain their replacement where they are edited.

### 3. High: unsaved answers and form designs can be lost

Evidence: `FormDesigner.tsx`, new-entry page and saved-entry page keep edits in component state. Close editor/back/navigation controls have no dirty-state protection. Setup displays a reminder but cannot protect the work.

Impact: navigating away, refreshing, losing a tab, or an expired session can discard work before a successful save. This is especially costly on phones and interrupted networks.

Required change: show unsaved/saving/saved state; intercept intentional in-app departure with Save / Discard / Stay; protect refresh where supported. Offer an authorized server draft save and explicit retry. Do not silently persist confidential answers to browser local storage. Designer save controls should freeze changes during an in-flight save or retain edits made after the save began.

### 4. Medium: backend errors do not guide users to the question

Evidence: new entries flatten server error strings into a notice; saved entries display only `normalizeApiError(...).message`. Neither applies server field errors to `DynamicForm`. The normalizer also ignores nested object-shaped field errors.

Impact: users can receive a generic failure with no usable correction path, particularly for structured items. Client required-field checks only test presence and do not validate item rows or scalar formats.

Required change: normalize nested field/item errors into a usable structure, associate errors with questions and item rows, and focus the first invalid editable control. Provide a linked error summary. Retain answers and pending files on every failed save/upload/submit.

### 5. Medium: numeric controls do not express their rules

Evidence: `DynamicForm.tsx` supplies number type/inputMode to INTEGER/DECIMAL but no scalar step/min/max. ITEM_LIST has explicit quantity bounds/step.

Impact: decimal spinner behavior defaults to whole steps; configured backend bounds and precision are not visible. The entry page is not a native form, so browser validity is not automatically enforced on submit. Do not interpret the missing step as proof that manually typed decimals cannot be saved.

Required change: use whole-number step for INTEGER and an appropriate decimal step, mirror applicable limits, show unit/currency/precision guidance, and validate on the server. Positive financial amounts and totals need explicit business rules; generic DECIMAL alone allows negative values without configured minima.

### 6. Medium: company cards overstate readiness and mix versions

Evidence: `CompanyFormsWorkspace.tsx` labels every PUBLISHED item Ready to use, without checking `is_active` or backend START authority. Managers see builder results, including a published version and its draft revision as separate cards with the same name and no version displayed.

Impact: a published form may be unavailable to the current administrator's audience or inactive. Same-name versions make choosing the correct company draft difficult. Employees already receive filtered published forms from the backend, which should be preserved.

Required change: distinguish Published, Available to you, Draft revision, and Inactive. Group related versions for administrators, show the published version plus a clear pending-revision link, and derive entry actions from `allowed_actions`. Materials stage cards should explain that actions start from an approved request rather than suggesting an independent blank entry.

### 7. Medium: frontend shows inactive fields that submission snapshots exclude

Evidence: `DynamicForm` filters by conditional visibility but not `is_active`; template serialization includes the related fields; backend snapshot construction uses only active fields. Required checks in the new-entry page likewise iterate all template fields.

Impact: a template containing an inactive field can show a question absent from its submission snapshot, potentially creating a misleading required-field check or unknown-field error. This is a conditional source-level defect; no live company fixture was reproduced.

Required change: consistently filter active fields in display, client validation, defaults, and payload construction; preserve old snapshot fields for historical entries according to their saved schema.

### 8. Medium: structured-question accessibility is incomplete

Evidence: scalar fields have ids, labels and described-by help/errors. ITEM_LIST's outer label points to a fieldset, not a labelable input; its item inputs do not receive the parent error/help association. LOCATION controls do not receive the complete parent association either. MULTISELECT uses a native multiple select without selection instructions.

Required change: give structured groups proper legends, individually named controls, per-row errors and described-by links; use a keyboard-friendly multi-choice control with understandable selection instructions. Verify keyboard focus after item addition/removal and failed submission with a screen reader. Maintain the existing minimum control sizes and ordinary scalar labels.

### 9. Medium: editing choice labels rewrites stored option values

Evidence: `FormDesigner.tsx` renders choices as comma-separated labels and, on any edit, rebuilds each choice as `{value: label, label}`. Existing stable values such as `cash` can become `Cash`.

Impact: conditional show_when comparisons, integrations, or reporting conventions can change when an administrator only intended to rename a display label. Historical schema snapshots remain separate, but the new revision's semantics change.

Required change: preserve stable option values while editing labels, expose individual choice rows, and make value changes deliberate. Validate unique values and any conditional references before saving. Avoid comma-only editing for labels that contain commas.

### 10. Medium: library cards need decision support, not more decoration

Evidence: library cards show category, description truncated to two lines, field count, automatic-details indicator, preview and selection actions. Existing company copies are matched by code, so custom copies made with a suffix still appear unselected for the original template.

Required change: show purpose, intended submitter, review/setup requirements and company selection state (Saved draft / Published / Update available). Link to related customized company copies using provenance while retaining the ability to add another intentionally. Keep one clear preview action and one selection action; show selected count and a clear selection reset. Preserve search/category state and preview keyboard-focus return. Use equal card spacing without stretching short descriptions into large empty areas.

### 11. Medium: financial and personal narrative templates rely on administrative care

Evidence: starter `question()` defaults to NORMAL. Payment amounts, expense amounts, leave narratives and incident narratives mostly retain that classification, despite descriptions warning about restricted use. Identity defaults are PERSONAL.

Impact: instructions alone do not enforce financial/HR confidentiality, particularly when Published audience sharing is enabled. This is a policy-design gap; it is not proof that every financial field must be confidential for every company.

Required change: define intended classification per library question and offer sensible access presets by form purpose. Show privacy implications during selection/publication. Support authorized company customization without assuming every employer has the same disclosure policy. Restrict HR/incident files consistently with the chosen policy.

### 12. Medium: retry recovery has a remaining duplicate-creation risk

Evidence: `saveFormWithFiles` correctly remembers the draft after a successful create response, uploads sequentially, removes successful uploads from the pending list, and stops before submission on a file failure. A lost initial create response leaves `savedId` null; retry can create another draft. No create idempotency token is supplied by this frontend transport.

Required change: use a stable per-entry creation token with a tenant/actor-bound backend idempotency contract. Distinguish saved draft, uploading, submitted, and unknown response state. Verify response-loss retries separately from file-upload failures. Material movement references already have their own retry protections; those do not cover generic draft creation.

## All 23 source designs

These are structural assessments and proposed improvements, not claims about each company's current saved form. Every design should retain trusted identity defaults, editable company-date/location defaults where appropriate, plain instructions, and a compact optional-details section. Add cross-field business rules server-side before relying on them in reporting.

| Design | Fields | Structure and next improvement |
|---|---:|---|
| Goods collection form | 7 | Structured item rows are suitable. Add optional source/receipt reference when traceability is needed; keep quantities positive and units mandatory. |
| Vehicle request | 8 | Destination/date/purpose are clear. Consider departure/return time, passenger count and transport constraints when relevant; explain reviewer and outcome. |
| Daily report | 7 | Useful completed work/support/next steps. Consider structured measurable results for companies that need reporting totals. |
| Inspection checklist | 7 | Currently location/pass/findings, rather than a true repeated checklist. Offer configurable check rows, per-check outcome, corrective owner and due date. |
| Weekly progress report | 8 | Results/challenges/next steps are suitable. Define the reporting week and prevent ambiguous period boundaries. |
| Branch operations summary | 9 | Explicit start/end dates. Require end ≥ start; make metrics configurable rather than relying entirely on narrative. |
| Request materials from headquarters | 9 | Structured items and linked journey are appropriate. Make audience, needed-by date and approval route readiness visible. |
| Materials dispatch / delivery note | 9 | Must start from an approved request. Show permitted remaining quantities and derive linked references instead of requiring independent matching. |
| Confirm materials received | 9 | Must start from a delivery. Keep missing/damaged details, remaining quantities and partial receipt visible. |
| Return materials | 8 | Must link to a receipt. Explain returnable quantities and whether replacement remains due. |
| Payment collection form | 10 | Amount/currency/method/reference support review. Define financial access, positive/zero rules, payer/context needs and duplicate reference policy. |
| Daily collections summary | 8 | Total/currency/references are useful. Consider deriving totals from individual records to avoid re-entry and reconciliation errors. |
| Expense approval request | 9 | Appropriate purpose/estimate/currency/date. Define amount rules, approver and whether supporting evidence is expected. |
| Purchase request | 10 | Free-text items currently hinder totals. Consider structured goods/services with quantity, unit and estimated unit cost where useful. |
| Expense reimbursement | 8 | Amount/date/receipt reference are useful. Define financial privacy, evidence requirements and duplicate-claim safeguards. |
| Leave request | 8 | Dates/type/handover are suitable; no general medical details. Require end ≥ start and clarify duration/company leave policy. |
| Attendance correction | 6 | Current correction is narrative. Add original date/time and proposed date/time/status for reliable administrative handling. |
| Employee service request | 7 | Flexible request/details/needed-by. Offer service categories and service-specific routing without collecting unnecessary personal detail. |
| Stock movement | 8 | Items are free text. Use structured quantities/units and validated source/destination locations if stock accounting is expected. |
| Stock count | 6 | Counts are free text. Use rows for item/unit/expected/counted/difference; retain discrepancy explanation. |
| Equipment issue and return | 8 | Action/asset/holder/condition support the task. Consider asset selection, linked issue for return and condition evidence. |
| Maintenance request | 8 | Location/problem/urgency/date are helpful. Clearly explain that submission is not an emergency response; show assignment and follow-up status. |
| Incident report | 7 | Operational date/location/facts/action are useful. Add optional severity/follow-up owner and restricted access presets; keep sensitive personal detail out of general sharing. |

## Desired page behavior

Library: search and meaningful category filters → concise purpose/setup card → full interactive preview marked Answers are not saved → add company draft → direct link to review that draft. Public library content contains no company answers, recipients or attachments.

Company administrator: group related versions → clearly separate saved drafts and published forms → preview questions → review route → review submission and reading audiences → publish → see readiness and pending updates. Bulk selection should remain atomic and never overwrite customized copies.

Employee: see only backend-eligible forms → one Start entry action → trusted automatic details → clear required fields and structured errors → explicit draft-save status → supporting files → visible reviewer summary → submission receipt with reference and progress → return/correction using the historical schema.

Appearance: preserve the theme-aware shared sheet and mobile single-column layout. Use consistent category names between library and company cards. Reserve strong colors for actions/status, keep descriptions readable, distinguish previews from live entries, and ensure fixed headers/bottom actions do not obscure focused controls. Test long names, instructions, options, large item lists, text zoom and native keyboards. Decorative icons currently distinguish expense/HR categories that are not actual template categories; use a shared category mapping if purpose-specific icons are desired.

## Security foundations to preserve

Source review found tenant-scoped template queries, explicit capabilities and backend allowed_actions, audience intersections for ordinary form use, separate sensitive-form configuration authority, immutable historical schema snapshots, company-serialized library selection/revision/publication, conditional-answer pruning, server-trusted identity defaults, field redaction with preservation of masked saved values, and private file checks that require clearance for every schema classification unless explicitly authorized sharing applies.

These are useful controls, not a certification. Retain them while improving the frontend. UI hiding must never replace server authorization. Verify attachments through the object-scoped download endpoint and keep confidential content out of client persistence, logs, analytics and previews. Logout clears the main query cache; do not describe identity-less query keys alone as a demonstrated tenant leak. Scope library company-copy and designer-choice cache keys by company and actor for consistency and validate session changes in practice.

## Required completion evidence

1. Use the configured Python environment with all project dependencies and rerun the focused form/security suite and frontend contract checks. Run frontend type-check/lint after implementation changes.
2. Inspect actual active library rows and all selected/published forms for the chosen test companies, including custom copies, revisions, inactive fields, classifications, audiences, routes and upgrade availability.
3. Use two disposable companies and administrator/manager/employee identities. Verify selection, revision, publication, submission, attachments, approval/return and cross-company denial without changing real production policy or sending business notifications.
4. Reproduce the high-priority findings with meaningful regressions: invalid typed values, audience widening, dirty navigation, nested errors, inactive fields, changed option labels and lost create responses.
5. Visually review all library previews and representative customized/published forms on narrow phone, tablet and desktop layouts in both themes. Verify keyboard and screen-reader behavior, 200% zoom, real mobile pickers and slow/interrupted connections.

Until all remaining evidence exists, describe the result as a structural/usability/security review with the authenticated coverage below, not a production-readiness certification.

## Authenticated follow-up — 12 October 2026

After the user supplied signed-in sessions, the review continued with Business Group Ltd's company administrator, Food Production manager and employee. The administrator completed email verification during the review. No credentials were retrieved or changed.

### Coverage completed

- Opened all 23 actual library previews. Verified their complete rendered questions, section grouping and explicit preview notice.
- Checked every library preview at measured 390×844 and 1280×900 viewports in the administrator's existing dark theme: 46 checks, zero horizontal overflow and zero input/select/textarea controls extending past the viewport boundary. These are desktop-browser viewport checks, not physical-phone, keyboard, text-zoom or screen-reader certification.
- Tested library search: `collection` returns Daily collections summary, Goods collection form and Payment collection form.
- Tested collection preview item addition/removal; two item-name inputs appeared after adding a second row. Returning to the library restored focus to the originating `collection-record` preview button. No selection or entry was saved.
- Opened all 14 visible company selections and read their current state/version, complete preview, review summary, warnings and update notices. None showed horizontal overflow at the ordinary approximately 630-pixel browser width. These inspections did not expose every advanced saved access setting; the expense editor was additionally inspected without changing it.
- Opened both forms available to the employee and manager: Daily collections summary and TEST - Food Production daily report. Reviewed the employee's returned test entry and the manager's read-only view of a colleague's draft.
- Inspected the Attendance correction publication panel and the Expense approval request editor, then closed both without saving or publishing. Restored temporary viewport overrides.

Raw evidence: `forms-live-preview-checks.json`, `forms-live-responsive-checks.json`, and `forms-live-company-checks.json`. Screenshots: `forms-library-preview-live-review.jpg`, `forms-library-desktop-live-review.jpg`, `forms-company-live-review.jpg`, and `forms-returned-live-review.jpg`.

### Current company selections

| Selection | State/version | Live review observation |
|---|---|---|
| Attendance correction | Draft v2 | Supervisor route exists. Preview warns no reviewer resolves for the administrator's reporting location; employee resolution still needs a separate test. |
| Branch operations summary | Draft v2 | Library update advertised; no approval route; older five-question layout. |
| Confirm materials received | Draft v2 | Current context and structured-item layout; no independent route, appropriate for a connected confirmation. |
| Daily collections summary | Published v2 | Available to employee/manager; no approval route; older field ordering and blank date/currency on opening. |
| Daily report | Draft v2 | Current context/details layout; no approval route although the description says it is for the supervisor. |
| Employee service request | Draft v2 | Library update advertised; no approval route. |
| Equipment issue and return | Draft v2 | Library update advertised; no approval route. |
| Expense approval request | Draft v2 | Library update advertised; no approval route; five older fields with Normal privacy. |
| Goods or materials collection | Draft v2 | Older single item/quantity/unit layout differs from library Goods collection form with repeated item rows. |
| TEST - Food Production daily report | Published v2 | Employee can start an entry; branch-manager review is displayed. Administrator has management actions but no Fill in form action for this audience. |
| TEST - Materials Dispatch | Draft v3 | Library update advertised; independent review not configured. |
| TEST - Materials Receipt | Draft v2 | Library update advertised; independent review not configured. |
| TEST - Materials Request | Draft v2 | Library update advertised; branch manager then headquarters review displayed. |
| TEST - Materials Return | Draft v2 | Library update advertised; independent review not configured. |

Totals: 12 drafts, two published selections, eight visible update notices. Test-labelled forms remain test fixtures; their presence is not evidence of operational readiness.

### Additional confirmed findings

**Older company copies need a reliable comparison with the library.** The live library's Daily collections summary puts About this entry first and identifies its date/currency defaults. The published company copy puts this context after Form details, opens with blank date/currency, and advertises no update on its card. The Goods collection company draft uses a different name and older single-item structure while the current library uses repeated rows. The exact baseline/signature reason for a missing update notice was not established from UI evidence. Investigate the saved starter snapshot and proposal comparison before changing update logic; do not overwrite company customization automatically.

**Approval-purpose forms need explicit route readiness.** Expense approval request currently has Approval workflow = No approval required, and Where this form goes = Saved without an approval route. The estimated amount's Answer privacy is Normal. These are confirmed saved configuration states, not merely starter recommendations. Before making this form available, require an explicit decision to configure approval or intentionally operate without it. Show that decision prominently alongside audience/privacy. The backend currently requires a route for material requests, but does not impose the same requirement on all forms named approval requests.

**The existing draft protections work in the sampled manager view, but the wording is misleading.** The manager can see the employee's Daily collections summary draft through existing authorized-colleague access; its personal identity answers are masked, files are restricted, all answers are read-only, and Save/Submit controls are absent. This is consistent with server-authorized colleague visibility rather than audience sharing. Publication text saying Drafts remain restricted should explain that existing authorized colleagues can still see them. On a read-only DRAFT, masked text says Its saved value will be preserved and file text says Files are locked after submission; both describe editing/submission behavior instead of why this account lacks authority. Replace with context-specific read-only guidance.

**Returned-entry presentation is useful.** The employee sees Changes requested, a clearly separated reviewer note, historical version, editable answers, the saved test attachment, and Save/Submit controls. No correction or resubmission was performed. The manager view demonstrated personal-answer masking and file restriction; actual download/export enforcement and second-company isolation remain untested in this browser pass.

**Visual hierarchy can be improved without redesigning the form engine.** Dark library previews and light employee entries were readable in sampled screenshots. Library controls occupy most of the initial phone screen, so compact search/category/selection spacing would bring cards into view sooner. Draft badges use a similar green tone to ready states; distinguish Draft from Ready consistently. Keep the proven preview focus return and two-column desktop card layout. Longer validation messages, actual mobile keyboards and 200% zoom still need testing.

**Transient loading needs investigation only if reproducible.** The manager's forms screen remained as placeholders during initial navigation, then loaded correctly after one refresh. Browser console inspection showed no captured error. The development server also displayed compilation indicators. This is a recorded observation, not a diagnosed production defect.

### Remaining security and release limits

All three inspected browser accounts belong to the same company. A second-company browser session, newly submitted live entries, live cross-company object/download denial, actual network-loss retries, real mobile devices and screen readers were not exercised. No publication, library selection, draft save, file upload/removal, correction, approval, or company permissions were changed. The subsequent isolated verification below resolves the dependency-blocked regression suite and checks cross-company API/file denial with disposable test companies. The shared-validator defects remain unresolved.

## Final checks before implementation — 12 October 2026

### Security suite now runs successfully

Installed the repository-declared passkey dependencies into the temporary `.review-deps` workspace directory, without changing the global Python environment, requirements, or application settings. A second setup issue was Windows denying access to pytest's normal temporary directory. Using a fresh, explicitly checked workspace temporary directory resolved it.

The final focused suite passed **25 tests in 66.63 seconds** across:

- Form library selection, rollback, tenant ownership and explicit review audiences.
- Trusted identity/company/timezone defaults and preserved drafts.
- Version history, customized catalogue updates and stale-update rejection.
- Location-based publication, confidential-sharing authority and confirmation.
- Cross-company entry denial and cross-company private-file download denial.
- Attachment restrictions, locked files and subscription upload limits.
- Return → correction → resubmission → approval with the same entry/file and unauthorized-review denial.
- Active workflow requirements, connected materials quantities/retries/permissions.
- Shared forms integrated with business requests and field activities.

These use an isolated test database and disposable fixtures; they do not change live company selections or user access. The tests confirm the covered security behavior, not comprehensive security certification. They do not cover the invalid scalar values and renamed-file weakness reproduced separately below.

### Retry behavior reproduced using the actual frontend helper

The actual `saveFormWithFiles.ts` function was executed with a simulated transport, without HTTP requests or uploads. Evidence: `forms-retry-checks.json`.

- Failure during the second upload retained the saved draft id and the remaining file. Retry updated that same draft, did not repeat the successful first upload, and submitted only after both files succeeded.
- Loss of the first create response after a simulated server commit left the client without a saved id. Retry issued a second create and produced two simulated drafts. This confirms the earlier duplicate-creation concern. Add a stable, actor/tenant-bound creation token and a recoverable response contract; do not enable blind automatic retries.

### Company baseline discrepancies diagnosed

Read only configuration metadata for the exact company shown in the authorized administrator session. No submission answers, user details or attachment contents were read by this check. Evidence: `forms-company-baseline-checks.json`.

- Daily collections summary has a saved baseline equal to the current library snapshot, while its existing five business fields differ from the latest library definitions. The update indicator compares the baseline to the library, so its absence is expected under the current algorithm. **Do not fix this by automatically replacing company fields.** Show a separate Customized / Differs from library state and an explicit comparison if desired.
- Goods or materials collection has no `source_starter` or saved starter baseline. It therefore cannot receive provenance-based library updates, despite the library linking to it by matching its code. Treat it as an unlinked legacy/custom copy; offer an explicit, reviewed migration/copy path rather than silently assigning provenance or replacing its single-item structure.
- Eight other selections have starter provenance but no saved baseline. This matches their update notices. The update proposal must preserve potentially intentional field changes and present added/replaced/retained questions clearly.
- None of these 14 visible selections currently enables confidential audience sharing. Most have no person/position restriction; the old goods form has a fixed organizational scope. This does not remove the need for a deliberate publication audience review when configurations change.

### Additional security finding: extension-only file validation

**High priority before production use of attachments.** `documents.services.validate_uploaded_file` checks size and filename extension, then guesses MIME from the filename. A database-independent probe accepted synthetic non-PDF bytes named `receipt.pdf` as `application/pdf`. The frontend uses the same extension-based eligibility approach. Evidence: `forms-validation-checks.json`.

This proves file-type spoofing acceptance, not execution of malicious code. The reviewed application upload path contains no content-signature validation or scan/quarantine state; an external scanning deployment was not established by this review. Private access and download authorization still pass the focused security tests.

Required change: verify actual file content against supported types, enforce format/size constraints safely for images and Office archives, and require a configured scan/quarantine verdict before download where the deployment's security policy requires scanning. Keep files private, preserve author/reviewer checks, and do not treat a filename/MIME guess or `nosniff` header as malware verification. Add regressions for renamed content and safe rejection without abandoning the saved draft.

### Expanded scalar validation evidence

`forms-validation-checks.json` confirms invalid TIME `25:99` and invalid DATETIME strings are also accepted. DECIMAL `NaN` with a minimum bound and a malformed numeric minimum raise `InvalidOperation`, instead of a field `ValidationError`. Validate configured rule types when saving a design as well as validating answers. The earlier DATE, EMAIL, fractional INTEGER and non-finite DECIMAL findings were reproduced. A control case, BOOLEAN text `true`, was correctly rejected.

### Additional usability finding: search entry link mismatch

**Medium priority.** `GlobalSearchService._forms` returns `/form-submissions/{id}`. `GlobalSearch.tsx` passes the internal URL through without rewriting it, while the frontend entry page is `/forms/submissions/[submissionId]`. No corresponding old route or rewrite was found in the current frontend. Correct search links to the real entry page and verify returned/historical entries open with their existing authorization. Search itself uses the tenant-scoped visibility service; this finding concerns navigation, not demonstrated data disclosure.

### Frontend contract review

The scanner parsed 298 client calls and 46 capability constants: zero unknown capabilities, zero unresolved calls, and one computed URL requiring manual review in `companyStructureApi.ts:37`. Inspected its five literal callers—branches, departments, teams, positions and employees—and confirmed all five resolve to backend GET routes. The automated scanner still exits with its manual-review flag; do not report that command as an unqualified green run. Raw report: `forms-contract-checks.md`. This is static route/capability verification, not a runtime payload or permission test. Earlier frontend TypeScript checking passed; frontend source has not changed during this review.

### Implementation order supported by the completed checks

1. Repair server answer/rule validation and attachment content handling; add focused regressions for the reproduced defects.
2. Make publication audience changes deliberate and reviewable; make approval-purpose forms explicitly choose a valid route or intentional no-approval behavior.
3. Protect unsaved work, add draft-create idempotency, and attach server errors to the precise question/item.
4. Improve company readiness/version labels, legacy/custom-copy comparisons and reviewed catalogue upgrades without rewriting history or company customizations.
5. Refine structured-question accessibility, choice-label editing, numeric controls and compact library browsing; then improve individual template structures according to the catalogue table.

The code/API checks now provide sufficient evidence to start those improvements. Physical phones, native keyboards, screen readers, zoom, production file scanning/storage, deployment conditions and populated staging journeys remain release acceptance work. They should not delay safe, reversible implementation of the confirmed defects, but no production-readiness claim should precede them. No company configuration or application behavior was changed by this review.
