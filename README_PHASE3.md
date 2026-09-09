# SmartBiz Phase 3 — Security Control Plane

This package hardens `security`, `support`, and `platform_admin` around the production architecture established in Phases 1–2.

## Implemented
- Immutable authoritative audit records.
- Hashed/HMAC OTP challenges; plaintext OTPs removed from storage.
- OTP expiry, attempt limits, challenge IDs, issuance rate limit.
- Cryptographic trusted-device token design instead of browser/OS fingerprint as proof.
- Session termination preserves evidence and blacklists refresh-token JTIs.
- User/company session revocation helpers.
- Hashed failed-login principals instead of retaining raw email in the lock table.
- Tenant security permissions use capabilities, not `ADMIN`/`SUPERUSER` role shortcuts.
- Platform security functions are split into platform capabilities.
- Support ticket sensitivity classification.
- Tenant support visibility no longer means every Company Admin sees every sensitive ticket.
- Customer-visible support messages and internal support notes are distinct.
- Support ticket state machine is service-controlled.
- Customer reply to RESOLVED reopens the case; CLOSED remains closed.
- Support notifications should carry generic references, not message-body snippets.
- Controlled Support Access / Support Mode model and service.
- Support access requires explicit scopes, reason, expiry, separate approval, and audit.
- Compensation, HR-confidential, private chat, precise location, private documents, sensitive custom-form data and official-record snapshots are excluded from ordinary Support Mode.
- Platform serializers are summary-oriented and avoid exposing raw activity metadata/email-delivery internals by default.

## Required capability constants
Phase 1 must include:
`VIEW_COMPANY_SECURITY`, `VIEW_COMPANY_AUDIT`, `VIEW_COMPANY_SESSIONS`, `TERMINATE_COMPANY_SESSIONS`, `VIEW_COMPANY_SUPPORT`, `MANAGE_COMPANY_SUPPORT`, `VIEW_SENSITIVE_SUPPORT`, `PLATFORM_SUPPORT`, `MANAGE_PLATFORM_SUPPORT`, `MANAGE_PLATFORM_COMPANIES`, `MANAGE_PLATFORM_USERS`, `MANAGE_PLATFORM_SUBSCRIPTIONS`, `VIEW_PLATFORM_SECURITY`, `VIEW_PLATFORM_HEALTH`, `PLATFORM_ADMIN`.

## Migration notes
1. Security OTP data migration: invalidate/delete all outstanding legacy plaintext OTP rows rather than migrating plaintext codes.
2. TrustedDevice: invalidate legacy fingerprint trust and require clients to establish a new random device token after successful MFA.
3. ActiveSession: add `terminated_by`, `termination_reason`, `termination_note`, `created_at`; preserve existing rows.
4. FailedLoginAttempt: migrate to `email_hash`/`email_hint`; legacy rows may be safely expired and recreated.
5. AuditLog: add UUID PK/metadata if not already available; application code must never update/delete audit rows.
6. Add `SupportAccessSession`.
7. Support: add sensitivity/requested_priority/closed_at and message visibility.

## Integration requirements
- Wire Phase 2 user deactivation/password reset/termination to `terminate_user_sessions()`.
- Replace direct session `.update(is_active=False)` calls with `terminate_session()` so JWT JTIs are blacklisted and evidence is retained.
- Replace the old VerifyOTP flow with challenge_id + code + optional trusted-device token flow.
- Platform `security/audit/login-history` endpoints must use platform capability permissions.
- Tenant company-security endpoints must never expose other companies.
- Platform dashboard should show platform/security telemetry only, not tenant operational ActivityLog contents.
- Support Mode must be a request context/session feature; it must never modify the support agent's company or impersonate a customer.
- Frontend later must display an unmistakable SUPPORT MODE banner with company, scope, ticket/reason and expiry.
