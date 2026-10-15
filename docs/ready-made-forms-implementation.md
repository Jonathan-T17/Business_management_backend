# Ready-made forms implementation journal

Approved journey: Library → private Company forms draft → review and adjust → publish → open, complete and submit.

## Delivered

- All 23 stock library designs include prepared fields, instructions, examples and sections.
- Goods collection form includes collector, company, collection date, location, collection type, item/quantity/unit rows and optional notes. Payment collection is a separate form.
- Shared previews contain no company identity, employee data or submitted answers.
- Selecting library cards saves private company-owned drafts. Existing copies are not overwritten. Custom forms and copies remain company-private.
- Names remain the form title when opened. Company forms and saved forms use responsive cards.
- Employee and company identity are supplied by the server and read only. Company-local dates, assigned location and configured currency are starting values; editable defaults can be corrected.
- Opening and previewing do not save submissions. Save draft and Submit are explicit actions. A failed submission reuses its saved draft when retried.
- Ordinary published company forms are available to active, assigned company members without a separate form-use grant. Branch, department, team, audience and position restrictions remain enforced. Awaiting-position invitations do not receive this access.
- This does not grant access to colleagues’ answers, confidential data, configuration, company-wide analytics or approval decisions.
- A reviewed template update preserves custom wording, added fields and deliberately removed fields. It changes an unused draft or creates a draft revision of a published form. Publishing remains separate; historical submissions keep their schema snapshots.
- Update review tokens reject concurrent library and company-draft edits.
- The editor supports section headings and automatic starting values while preserving conditional-field settings.

## Existing company forms

Existing company-owned forms keep their current content. Copies linked to a library source display an update notice and a Prepare updated draft for review action. Older copies without a captured library baseline preserve all existing fields; review for duplicates before publishing. Forms not linked to a library source can be edited or replaced with a new company copy from the library.

## Validation

- 27 backend tests passed across form journeys, governance, material movements, position scope, assignments and attachments.
- Three additional malformed automatic-value cases tested separately; all rejected safely.
- Frontend type checking and lint checks passed for all ten changed files.
- Strict API schema validation passed. No pending model changes.
- Local catalogue migrations applied; 23 of 23 stock forms match the complete library designs.
- Live company-admin library preview and employee published-form opening checked in dark mode. Responsive preview verified at desktop and normal narrow workspace widths without horizontal overflow.
- No operational submissions created or approval decisions made during the browser review.

## How administrators use this

Open Forms and select Ready-made library, preview a card and add it to Company forms. Open the saved draft, review its fields and approval destination, then publish when ready. Workers open the published form from Company forms. Special material confirmations still start from their approved request.


## Navigation refinement — 3 October 2026

Company forms opens first. Administrators browse the Ready-made library in a separate tab, open saved cards within the same workspace, and return with Back to forms. Card descriptions are limited to two lines. Rare actions appear under More options; update details and approval settings expand on request. Submissions is a separate entry view with its existing server-authorized scope. Duplicate Form library navigation and the local Forms navigation row have been removed. Existing URLs continue to work.

Saved company forms now load across all API pages so searching does not omit later forms. Frontend type checking and lint passed. Live administrator cards, library switching, form opening/return, submissions and keyboard tab navigation were checked; employee cards show no administrator controls. No forms or work entries were changed by these checks.

### Opened form visual refinement - 3 October 2026
- Applied the user-provided reference: green title band, aligned desktop label/control rows, stacked mobile fields, subtle dividers and a prominent submit action.
- Shared renderer retains form-specific fields, automatic values, conditional visibility and validation. Dropdown prompts now name the field.
- Reviewer details are collapsible; routing warnings remain visible. No company data or access rules changed.

- Verification: TypeScript and focused ESLint passed. Live visual verification attempted; workspace readiness and form loading did not complete during this pass.
- Browser follow-up: fresh reload succeeded. Verified the published Daily report with the new title band, field layout and dark-mode narrow viewport. Screenshot: docs/form-reference-design.png. No entry submitted.

### Shared form design - 3 October 2026
- Added one reusable green-header form layout for all library templates, company previews, new entries, saved entries and connected material form fields.
- Retained form-specific schemas, identity defaults, permissions, routing and validation. No records published or submitted.
- Enlarged field text and controls; goods item rows are visible on first opening.
- TypeScript and focused lint passed. Verified collection library preview in light desktop and dark narrow layouts; restored original theme and viewport. Screenshot: docs/shared-form-design-desktop.png.


### Library-first selection - 3 October 2026
- Form headers now use shared theme colours instead of a fixed green.
- Administrators start in Form library; Chosen company forms holds their saved selections and private custom forms.
- Default templates remain global library records; the existing select-starters endpoint creates a tenant draft only after an explicit selection. Existing company records were preserved.


### Company form selection reset - 3 October 2026
- At the administrator's request, retired all 14 active forms for Business Group Ltd (company 3). Active selection count is now zero; 4 saved entries and 23 shared library designs remain intact. Other companies were not changed.
- Selecting a retired library form now creates a fresh draft revision from the current library design, with old scope and workflow assignments cleared. Historical versions remain intact.
- Regression suite: 7 library tests passed; frontend focused lint passed.


### Dedicated previews and responsive review - 4 October 2026
- Replaced card disclosures with a dedicated complete-form view; retained library search and selections on return.
- Added keyboard focus restoration, header scroll clearance, and larger item-removal touch controls.
- Completed 92 local viewport layout checks across 23 templates. Added docs/forms-device-review.md for the real-device and populated staging checks required before production. No company forms selected or entries submitted during this review.

## Compact visible forms (2026-10-04)
Shared form sheets now use smaller headers, 44px controls, tighter rows and two-line expandable notes. Desktop notes align beside their labels. Standard identity/date/location help is shorter; custom guidance and all existing fields remain available without new reveal buttons. Existing conditional applicability, validation and permissions are unchanged. Goods collection preview checked at 390px and 1280px: nine controls, no horizontal overflow or clipped controls. TypeScript and focused ESLint passed. Native Android/iOS checks remain for pre-production.


## Separate item entry (2026-10-04)
Existing repeated ITEM_LIST fields retained. Each group now has an Item number and an Item name label; Add another item is a prominent themed button. Browser preview verified adding a second and third item, entering independent name/quantity/unit values, and removing the third without losing the first two. Preview-only sample answers were not submitted. TypeScript and focused ESLint passed.

