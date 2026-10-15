# Forms improvements — 12 October 2026

Implemented following the deep review in `forms-deep-review-2026-10-12.md`.

## Company-facing changes

- Library cards group forms by purpose, show question counts and distinguish saved drafts, published forms and adapted copies. Company cards show version and draft/published/usable status. Saved entries support company-scoped server search and status filters.
- Questions hide inactive fields, expose numeric and text limits, associate errors with inputs and provide a focusable error summary. Structured item/location questions have accessible labels; multiple-choice questions use checkbox groups.
- Draft editing keeps choice values stable when labels change. Conditional questions use valid earlier scalar fields and explicit choice values. Invalid numeric rules and duplicate choices are rejected.
- Unfinished form answers and edits prompt on application links, editor close and form navigation, with Stay / Discard / Save options. Refresh and window close use the native browser warning. Browser Back/Forward is guarded where the Navigation API supports cancellable traversal (verified in the current Chromium browser); physical-device and other-browser behavior still needs staging checks.
- Stable request keys prevent duplicated drafts after a lost create response. File retries retain the original draft and remaining files. A lost submit response is resolved by checking the saved status before resubmitting. Keys are bounded to company, author and original form; retry never silently overwrites saved answers.
- Publication starts from saved settings, preserves existing restrictions and requires deliberate confirmation before clearing/widening access. Request templates without approval require an explicit no-approval decision; materials requests still require their approval route. Confidential-sharing controls remain separate.
- Library update review reports customization, missing baselines, changed and removed questions. It does not reset company questions automatically. Form search links now open the correct entry page.

## Validation and file safety

The backend rejects impossible dates/times, invalid emails, fractional whole numbers, booleans passed as numbers, non-finite decimals and malformed bounds. Required whitespace-only answers fail validation. New unchanged monetary library defaults enforce a minimum of zero; existing company copies retain their own rules.

Uploads receive content validation instead of trusting extension alone. Images are decoded within pixel/frame limits; PDFs are parsed and encrypted PDFs rejected; Office ZIP/XML content is bounded and macro/ActiveX containers rejected; text is validated as text. Production additionally requires a clean scanner verdict before persistence, with fail-closed handling and private error messages. A ClamAV INSTREAM adapter and environment configuration are included. The real production scanner still needs provisioning and staging verification; see `deployment/RUNBOOK.md`.

## Verification

- 56 focused backend tests passed in 69.79 seconds, covering invalid/valid answers, schema rules, uploads/scanner failure behavior, tenant and author boundaries, retries, publication and correction workflows. One Windows pytest cache warning did not affect the tests.
- Frontend TypeScript check passed. Targeted forms lint passed before final history refinement; the final history hook and saved-entry filter received an additional lint check.
- The actual frontend helper regression harness passed: hidden/inactive/required questions, nested errors, sequential file retry and lost create/submit responses.
- Django system checks passed and no model migrations are missing. Local migrations 0020 and 0021 applied successfully.
- All 23 library previews passed at 390×844 and 1280×900: 46 checks, zero page overflow or clipped inputs. Evidence: `forms-implemented-responsive-checks.json`.
- Live administrator checks verified blocked expense publication without an approval decision, unsaved-edit Stay/Discard behavior and unchanged saved company name after discarding. Manager checks verified required-answer focus, browser Back protection, link navigation protection and server-filtered empty search results. The returned employee entry remains available for correction with its saved file.

No live company form was selected, edited, published or deleted, and no entry/file was created or submitted during implementation verification. Existing company access, customizations and history were preserved. Only the additive retry schema and unchanged global monetary defaults were migrated.

Screenshots: `forms-library-implemented.jpg`, `forms-publication-implemented.jpg`, `forms-unsaved-work-implemented.jpg`.

## Release checks remaining

Run clean/infected file checks against the actual private scanner and storage in staging; check mobile keyboards, touch controls and native Back/Forward on supported physical devices and browsers. Review company-specific approval routes/privacy classifications and proposed catalogue changes before publishing them. Historical answers are not rewritten automatically and may need author correction if newly validated edits expose invalid old values.
