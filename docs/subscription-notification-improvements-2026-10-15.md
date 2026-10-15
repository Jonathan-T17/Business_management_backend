# Subscription and notification settings

15 October 2026. Focused follow-up to the local system readiness review. No live subscription was cancelled or changed, no company notification rules were saved, and no email was sent.

## Changes

Subscription load failures now have their own retry state instead of appearing as an absent subscription. Available-plan failures are separate from an empty plan catalogue. Cancellation controls are hidden when subscription status cannot be confirmed. Tenant-administrator access remains consistent with backend authority, queries are account/company scoped, and cancellation reasons have a persistent label and unfinished-work warning. Successful cancellation clears the reason before refreshing status; existing confirmation and backend restrictions remain.

Available plans and company notification policies load every numbered page through fixed API endpoints. Repeated pages stop with a visible failure instead of looping or presenting partial results as complete. Array responses remain supported. The one-to-one current company subscription contract remains unchanged.

Notification rules have explicit loading, retry and empty states. Channel, recipient email-preference and rule-activation edits remain local until Save rule. Each edited rule supports discard and visible mutation errors; one shared leave warning covers all dirty rules and blocks navigation during a save. Inactive-rule guidance matches the notification service: default behaviour applies when the company rule is inactive. Rules affect eligible delivery, not record access.

## Verification and limits

- Production frontend build passed for all 92 generated pages, including TypeScript validation; targeted lint passed.
- Collection contracts passed for all plan/policy pages, fixed endpoints, duplicate-page detection, array compatibility and propagated network failures. Existing request-configuration contracts passed after the shared loader import change.
- Tenant subscription-control regression passed, including cancellation authority and foreign-company rejection. Notification-rule regression covers 26 records, all editable flags, forbidden employee updates and foreign-company isolation.
- Signed-in browser verified the real empty notification-rule state and populated subscription/plan view. Entered a synthetic unsaved cancellation reason, verified navigation warning and Stay, then cleared the reason. Cancellation was never requested.
- The live company has no notification rules; populated editor save/discard and failure paths were not exercised in the browser against live records. API mutations were checked in the isolated test database. Actual email delivery remains unverified.

Evidence: [notification rules](notification-rules-empty-2026-10-15.png), [subscription status](subscription-status-2026-10-15.png). Contract: `tests/contracts/subscription_notification_collections.cjs`. Backend regressions: `tests/security/test_notification_policy_settings.py`, `tests/security/test_tenant_subscription_controls.py`.

Remaining: optional-module configuration screens and broader failure/navigation/device states, final consolidated regression review, then isolated staging infrastructure checks. No deployment-readiness certification is implied.
