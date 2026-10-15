# Official-record issuance reliability

15 October 2026. Follow-up to the optional-configuration review.

## Confirmed defects and corrections

Report approval imported a nonexistent finalizer module/method. Request approval, plan completion and field completion did not call the source-aware finalizer. The older report/form workflow path attempted issuance without the required approval snapshot. These paths now use the existing source-aware finalizer, which constructs authoritative source and workflow snapshots. Request fulfillment and form approval retain their existing finalization calls.

Configured issuance also failed because the service supplied classification but OfficialRecord had no persistent classification field. Added the field and migration 0003. Existing rows receive SECURITY_SENSITIVE as a conservative migration value; the default for new rows is NORMAL, and the finalizer supplies the calculated classification. Existing source-visibility and export/issuance permission checks remain in effect. Historical record content is unchanged; its access may become more restricted until reviewed.

The rule API now validates active automatic source/status pairs: Report/Approved, Request/Approved or Fulfilled, Form submission/Approved, Plan/Completed and Field summary/Completed. Prefixes are normalized and invalid characters rejected. The editor offers only these supported statuses and explains the acting user's issuance authority requirement.

## Verification

- Five targeted tests passed: actual report/request adapter approval plus plan/field lifecycle services issuing four full records; repeat finalization producing no duplicates; missing issuance permission rolling back plan completion; invalid rule combinations/prefixes rejected; classification ceiling and request lifecycle regressions.
- Full snapshots preserve source fields and omit exact field coordinates. Tests use an isolated database. The source-handler test is not a full HTTP reviewer workflow or browser approval journey.
- Frontend TypeScript and targeted lint passed. Migration consistency check reports no changes.
- Migration 0003 applied successfully to the local database. No live source work was approved/completed, no rule was saved and no record content was edited in the browser.
- Signed-in browser verified Plan automatically selecting Completed and Report selecting Approved. The unsaved source selection was reset. Evidence: [record rule status](record-rule-status-2026-10-15.png).

## Remaining limits

Concurrency follow-up: record issuance now locks the saved source row before checking for an active record. A two-connection PostgreSQL test confirmed one returned record and one sequence allocation. The expanded workflow/delegation/record run passed all 22 tests; see the [consolidated status](staging-readiness-status-2026-10-15.md). This remains a focused concurrency check rather than production load certification.

Issuance is conditional on an active automatic rule and explicit ISSUE_OFFICIAL_RECORDS authority. Adding a rule does not grant that authority; an actor lacking it will receive an error and the transactional completion will roll back. New hooks do not backfill records for already completed work. The form approval path existed previously and was not newly covered by this focused four-source snapshot test. Broad workflow, historical-classification review, concurrent issuance, device and real staging infrastructure checks remain separate readiness work.
