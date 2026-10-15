# Platform security implementation — first pass

The user approved implementation following the 2 October 2026 review. This pass closes the session and platform-identity boundary gaps and corrects trusted-client-IP handling. It does not claim completion of the full security roadmap.

## Changes

- Login and OTP login bind access and refresh tokens to the saved active session using a signed session identifier. Protected requests verify that session belongs to the user, remains active and has not expired. Ending the session therefore rejects its existing access token on subsequent requests, without ending other sessions.
- Valid existing refresh tokens can acquire a session identifier through refresh rotation. Existing access tokens without a session identifier are rejected, allowing the frontend's normal refresh flow to upgrade them. A revoked or expired refresh session cannot be upgraded.
- Refresh rotation retains the session binding and rejects conflicting identifiers. Logout verifies refresh-token ownership before revocation and uses the shared termination service. Company session termination now also uses that service, preserving blacklisting and termination metadata.
- Platform-required password reset terminates existing sessions. Tenant lifecycle actions reject platform identities even when their role label is ADMIN. Lifecycle state and session changes are transactional. User summaries now expose authorized operational actions without advertising tenant lifecycle actions for platform accounts.
- Platform capabilities, legacy privileged permissions, advanced maintenance and recovery administration require an active staff superuser who is not deleted and has no required password change. Role-only platform identities remain excluded from tenant permissions and receive no platform capabilities or advertised privileged actions.
- Company support and legacy company-admin checks exclude platform identities. No live account flags or permission grants were changed.
- Client IPs are resolved from the direct peer by default. Forwarded headers are accepted only for configured trusted proxy networks; the chain is processed from the nearest proxy back to the first untrusted address. Invalid chains fall back to the peer. Login/verification/reset/public-verification throttles and audit creation use the same resolver.
- Platform counts and current-session lists exclude expired sessions. The inactive platform-session filter includes expired and terminated records.

## Deployment considerations

`TRUSTED_PROXY_NETWORKS` is an optional comma-separated list of exact proxy IP networks, for example `10.0.0.2/32`. Its default is empty. Invalid networks fail startup. Configure only actual trusted proxies, require the edge to strip or reconstruct forwarded headers, and prevent clients from reaching the backend through untrusted paths. Do not use a catch-all network.

Deploy token issuance, refresh and access-session verification together; mixed old and new authentication workers can issue access tokens the new workers reject. An old application rollback would remove immediate access-token revocation, so treat authentication rollback as a security decision. No database migration is required. Accounts with expired/revoked refresh sessions must sign in again; valid refresh sessions upgrade normally.

These changes deliberately do not grant platform privileges to accounts that only carry the SUPERUSER role label. If such an account was previously used as an operator, provision its authority through a reviewed privileged-account process rather than weakening the boundary.

## Verification

Real bearer-token tests cover active access, session termination, independent sessions, missing/malformed/foreign/expired bindings, legacy refresh upgrade, refresh rotation/blacklisting, logout ownership and role-only privilege denial. Proxy tests cover forged headers, trusted chains and malformed input. Existing real-token setup/form/support fixtures now create saved sessions instead of manufacturing unbound access tokens.

The first broad run passed 179 tests and exposed obsolete unversioned test URLs and strict schema warnings from earlier form work. Tests were updated to current versioned endpoints and paginated responses; missing computed-field types and a materials operation-name collision were corrected. Security assertions were retained.

The affected rerun passed 62 checks and identified missing user-action metadata. After correcting that contract, 30 focused tests passed, including strict OpenAPI generation/response validation, platform frontend contracts, personal security and session-boundary checks. The final targeted run passed all 18 tests, including the subsequent password-reset and platform-target safeguards. These selections overlap; the counts should not be added. Remaining warnings in schema tests come from the schema library's deprecated Python typing API; they are not OpenAPI-generation diagnostics.

Live platform browser verification retained administrator access and showed 13 current sessions instead of 81 accumulated records. Proof: platform-session-count-verified.png in the task visualization directory. Django system checks and migration consistency checks passed.

## Remaining approved roadmap

Recent-authentication controls for sensitive operations; privileged MFA and recovery; separate platform operator duties; temporary support-access workflow; incident management; stronger audit storage; measured service health; HttpOnly session/CSP migration; upload scanning; deployment verification and independent staging assessment remain separate implementation work. The existing green health badge still measures database/cache availability, not overall security assurance.


## Second pass

Administrator MFA, separate platform duties, incident tracking and measured reporting health are now implemented. See [phase-two implementation](platform-security-phase2.md) for behavior, migration requirements, verification and remaining deployment work. The earlier green database/cache health display has been replaced with explicit partial-monitoring states.
