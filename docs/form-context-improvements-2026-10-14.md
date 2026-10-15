# Form context clarification — 14 October 2026

The start-form page now displays the entry branch returned by the authorized initial-values endpoint. Work-site answers explain that they describe where work happened and do not change the filing branch, employee assignment or approval route. Prefilled work dates explain that creation and submission timestamps are recorded separately. Existing company-specific labels are retained; standard branch labels are presented as work-site details.

Verification: seven ready-form journey tests passed, including authorized branch metadata and cross-company rejection. Frontend TypeScript and targeted lint passed; strict API schema validation passed. No live entries, profile changes or access grants were saved.

Remaining: an authorized multi-branch filing selector, combined effective-permission previews, configured request-type fields and the remaining staging checks. This change alone does not establish deployment readiness.
