# Optional configuration reliability and field evidence

15 October 2026. Local follow-up to the system readiness review. No live field templates, record rules or document categories were saved or changed.

## Field configuration finding and correction

Source review confirmed that stop completion checks the configured additional form and its submission/approval status. The standalone require_location, require_photo, require_signature and require_notes flags are stored but are not enforced by that completion service.

The field settings page now uses an explicitly saved editor with readable activity types, active status and an additional published form. It explains the enforced form path and marks legacy evidence flags for review. New API attempts to enable those unenforced flags are rejected with a field-specific explanation. Existing true flags remain intact on unrelated updates and may be disabled deliberately. This is a compatibility safeguard, not implementation of GPS/photo/signature validation. Existing installations must review their legacy templates before relying on evidence requirements.

Form references unavailable in the current catalogue are retained unless deliberately changed. Updates omit an unchanged form reference, preserving existing references to retired versions. Form loading failures block saves. Draft navigation and replacement of the selected template require explicit discard.

## Record rules, document categories and lists

Record rules and category screens now provide readable labels/choices, visible list and save failures, retry, draft discard and leave protection. Inputs are disabled while saving. Successful creation resets the complete draft. The shared configuration list now renders its empty message for an empty array rather than leaving a blank section.

All field templates, record policies and document categories load numbered pages through fixed endpoints. The shared loader stops on repeated pages and propagates errors rather than presenting partial lists as complete. Query keys include the company and account.

## Verification and limits

Frontend TypeScript and targeted lint passed. Collection contracts passed with 26 records per collection, fixed endpoints and repeated-page rejection. Eight distinct field configuration/archive boundary tests passed across successful runs. The new field-template regression checks rejecting all four unsupported flags, supported creation and preserving/disabling legacy flags. Django system checks passed.

Signed-in browser checks verified the field editor and published-form choices, its discard warning, record-rule labels and leave warning, category labels/readable visibility and discard warning. All synthetic drafts were discarded or cleared. No live save was attempted. Screenshot: [field template settings](field-template-settings-2026-10-15.png).

The live company has no field templates, rules or categories, so populated editing and server-error states were not exercised through the browser. Official-record source/status compatibility and end-to-end issuance need a further semantic review; this batch improves the configuration interaction without certifying every issuance path. GPS/photo/signature enforcement outside protected form requirements remains unimplemented. Staging infrastructure and device verification remain open.
