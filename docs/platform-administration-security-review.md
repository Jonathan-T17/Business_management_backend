# Platform administration and security review

Reviewed 2 October 2026. Status: proposal awaiting user approval; no application, account, permission or infrastructure changes made during this review.

Follow-up: the user approved implementation. The first security pass is documented in [Platform security implementation](platform-security-implementation.md); remaining rows below describe the broader roadmap.

## Scope and evidence

Reviewed the platform frontend routes, navigation and API integration; backend platform permissions, maintenance controls, authentication, sessions, OTP, support-access services, audit models, upload validation, production settings and deployment runbook. Live signed-in browser inspection covered the platform overview, navigation, Security Center and System Health. This is a local code and browser review, not a penetration test or certification of deployed infrastructure.

Focused existing regression tests: 22 passed in 87.02 seconds across security control-plane, advanced maintenance, subscription renewal and organization/platform hardening tests. These tests establish a baseline; they do not prove the proposed missing controls work.

## Existing foundation to preserve

- Platform pages cover companies, users, subscriptions, support, sessions, failed logins, login history, audit, activity, health and advanced administration.
- Tenant and platform capabilities are separated. Platform identities do not automatically inherit tenant business-data permissions.
- Advanced maintenance requires an active staff superuser, no pending password change, password verification and a reason. Writes are throttled, transactional, restricted to listed models/fields and protected against stale edits and cross-company relationships.
- Email login challenges are hashed, expire, have attempt limits and are consumed once. Unknown devices require a challenge; trusted devices are revocable.
- Refresh tokens rotate and are blacklisted; refresh checks the saved session and account/company state. Services exist for terminating sessions and disabling accounts or companies.
- Audit records carry actor, target, severity and context. Individual model saves/deletes cannot modify existing audit records.
- Temporary support-access services restrict scopes, require a different platform approver and limit access to four hours. Confidential scopes are prohibited.
- Production settings enable HTTPS redirection, HSTS, restricted origins, secure cookies and short-lived signed object-storage URLs. These settings still require deployment verification.
- Keep plan changes in Subscriptions; keep renewal/reactivation in Advanced administration, with renewal and expiry dates clearly distinguished. Do not add the previously rejected shortcut from Subscriptions into Advanced administration.

## Findings and proposed remedies

| Priority | Observed condition | Why it matters | Proposed change |
| --- | --- | --- | --- |
| First | Access authentication checks account/company state but does not check the saved session. Access tokens last 30 minutes. | Terminating a session blocks refresh but can leave its issued access token usable until expiry. | Bind access tokens to a session and enforce revocation on requests; define idle, absolute and concurrent-session limits; test old tokens after logout, termination and credential changes. |
| First | Company session termination directly updates its row rather than using the shared termination service. | Blacklisting, termination metadata and auditing differ between entry points. | Consolidate all session-ending paths into one authoritative service. |
| First | Client-IP extraction accepts the first X-Forwarded-For value unconditionally. | An untrusted header can distort login lockouts and security evidence if the edge does not strip it. | Accept forwarding only from configured trusted proxies, sanitize it at the edge, and use consistent IP handling for throttling and audit. Verify the real deployment topology. |
| First | Platform identities receive all platform capabilities; a role-only SUPERUSER is recognized as a platform identity, while maintenance applies a stricter identity rule. | Routine support or billing work has unnecessarily broad authority; identity boundaries differ by endpoint. | Standardize privileged identity checks and introduce explicit platform permission groups: owner/recovery, security operator, customer support, subscription operator and read-only auditor. No automatic privilege grants during migration. |
| First | Login trusts a valid device token without OTP. No passkey/security-key authentication was found in reviewed authentication code; recovery admin uses a separate Django login boundary. | Privileged access and recovery need stronger authentication than remembered-device trust alone. | Require strong MFA for privileged users, preferably passkeys/security keys, with secure enrollment/recovery and recent authentication for sensitive actions. Apply equivalent protection to recovery admin, with a documented emergency-access process. |
| Next | Browser access/refresh tokens are kept in sessionStorage or localStorage, and production CSP allows inline scripts. | Script injection could expose bearer tokens. Existing CSP is helpful but incomplete. | Design HttpOnly secure session/refresh cookies or a server-side frontend session boundary, including CSRF/origin controls; migrate CSP to nonces/hashes and verify Next rendering compatibility. Preserve multi-account testing through isolated sessions. |
| Next | Overview shows 81 active sessions for five users; its query counts is_active without filtering expires_at. | The count can include expired records and is not a reliable current-session measure. It is not evidence of an attack. | Exclude expired sessions, distinguish current/recent/expired, clean stale sessions safely and show last activity, expiry and termination reasons. |
| Next | Security Center is a set of counters and navigation links. | It does not yet provide a managed incident queue or response workflow. | Add actionable incident cards, severity, affected accounts/company, investigation timeline, assignment, containment actions, evidence and resolution status. Zero events must not imply guaranteed safety. |
| Next | Overall health checks database and cache only. Email is called configured when an email backend exists. | Healthy does not confirm delivery, workers, scheduler, storage, backups or alert delivery. | Use distinct Healthy, Degraded, Unavailable and Not monitored states; add heartbeats, queue age, last job success, delivery failures and independently verified backup/restore evidence. Never show green for an unmeasured service. |
| Next | Temporary support-access models/services exist but a complete request/approve/end control-plane journey was not found in the reviewed routes. | An internal service alone does not provide an auditable operational workflow. | Add narrowly scoped temporary access requests, independent approval, expiry/revocation and a visible access history. Platform control must not become unrestricted access to tenant confidential records. |
| Next | Audit immutability is enforced by model methods, not demonstrated for database-level or bulk operations. | Application checks alone are not tamper-resistant evidence. | Explicitly read-only audit interfaces, database permissions/append-only protections, external protected log storage, retention rules and alerts when logging fails. Test bulk mutation and deletion paths. |
| Next | Document validation checks filename extension and size; MIME is inferred from filename. No content inspection/quarantine integration was found in reviewed upload services. | Renamed or malicious files can pass extension checks. | Inspect content types, quarantine pending scan, integrate malware scanning and restrict download behavior. Review all upload/import endpoints consistently. |
| Release gate | Production proxy, network isolation, secrets, backup restoration, alert delivery and clean deployment are described but not proven here. | Application UI cannot establish infrastructure security. | Verify HTTPS/proxy trust, private DB/Redis/storage, managed secrets and rotation, encrypted backups/restore drills, monitoring, dependency scanning, representative load and an independent security assessment in staging. |

## Frontend direction

Keep the platform recognizable but make it an operations workspace rather than a company dashboard. The landing screen should prioritize issues requiring attention and clearly separate customer operations, security incidents and service reliability. Show severity, timestamp/timezone, affected scope and a next action. Give security staff filters and investigation timelines; show confirmations that explain the affected accounts or companies before containment actions. Preserve readable cards, consistent navigation, mobile layouts and both themes.

Advanced administration remains a restricted recovery/configuration area. Everyday tasks should have dedicated understandable workflows. Financial records, confidential HR information and private company files do not become visible merely because someone operates the platform.

## Proposed implementation order and acceptance

1. **Close security boundary gaps.** Consistent platform identity policy, immediate session revocation, shared termination service, trusted-proxy handling and sensitive-action reauthentication. Verify denied tenant/role-only requests, revoked-token denial, unaffected valid sessions and audit records. Decide safe migration/recovery behavior before changing authentication.
2. **Secure administrator access and duties.** MFA enrollment/recovery, separated platform permission groups, temporary support-access workflow and stronger recovery administration. Privilege migration must preserve authorized administrators and avoid accidental expansion or lockout.
3. **Improve the control center and security evidence.** Accurate session counts, incident workflow, protected audit history, service heartbeats, explicit unmonitored states and consistent user-facing layouts. Verify populated, empty, error, mobile and dark/light states with representative operator accounts.
4. **Harden the whole application and validate deployment.** Session storage/CSP migration, upload scanning, tenant-isolation checks across modules, dependency checks, network/secrets verification, backup restoration, alert-delivery exercise and independent staging assessment. Define measurable release gates instead of promising that the system cannot be breached.

## References

- OWASP ASVS 5.0: https://github.com/OWASP/ASVS
- OWASP Session Management guidance: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- NIST phishing-resistant MFA guidance: https://www.nist.gov/document/sbccmfapdf

The implementation should use ASVS as a traceable verification checklist, with higher assurance for privileged control-plane and confidential-data paths. No compliance level is claimed by this review.
