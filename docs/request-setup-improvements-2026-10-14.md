# Request setup and draft completion

Implemented and checked locally on 14 October 2026. No live request types, routes, requests, files or employee permissions were created or changed during verification.

## Company experience

Request types now expose the supported amount, quantity, needed-by date and supporting-file requirements using Not used / Optional / Required before submission. Drafts can remain incomplete. Description, activation, a published additional form and an active request approval route are configurable. Reference codes remain stable on edit. Existing unavailable references are preserved unless deliberately changed.

The empty request page links authorized administrators directly to setup. Approval links open the route builder with Company requests selected. Reviewers still require an occupied position and explicit review permission; configuration does not grant access automatically. The careful-handling flag is a reminder, not a confidentiality permission.

## Employee experience and protection

Request entry reflects the selected type's actual policies and linked-form defaults. Draft details and answers can be completed and discarded explicitly. A central unfinished-work warning covers edits, notes and pending files; submission is disabled while other edits or uploads need completion.

Requests without an additional form now support authenticated file upload/download/removal. Writes require the requester and an editable draft/returned state. Linked-form files retain their existing protected path. Generic file representations do not expose private media URLs. Company isolation, existing validation, quota and scanner protections remain enforced.

Fixed employee read access to available request types, case-insensitive duplicate reference validation, trusted filing-branch derivation and linked-form branch consistency. Fixed PostgreSQL row locking during submission, which previously attempted to lock the nullable workflow join.

## Verification

- 16 request configuration, lifecycle and setup-route tests passed in the final focused run. A preceding successful run covered 17 document/report privacy tests: 33 distinct relevant tests across the successful runs.
- Configuration collection contract passed, including multiple pages, repeated-page detection and refusing to follow an untrusted next URL.
- Production frontend build passed for all 92 generated pages, including type validation. Targeted frontend lint passed.
- Django system checks and strict API schema validation with fail-on-warning passed.
- Signed-in browser verified the empty-state setup link, complete settings editor, unsaved-work warning, explicit discard and request-specific approval route selection. Synthetic settings were discarded without saving.
- Visually inspected screenshot: [request settings](request-type-settings-improved-2026-10-14.png).

Live create/upload/submit was deliberately not exercised against company records; those mutations were verified in the isolated test database. This is not a whole-suite or production infrastructure certification.

## Still open

Continue guided company setup simplification and remaining navigation, pagination, error and unfinished-work coverage. Separately verify real email, private storage, malware scanner, worker/broker, backup restoration and phone interaction in isolated staging before public deployment.
