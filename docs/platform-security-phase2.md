# Platform security: administrator access and operations

Implemented 2 October 2026 following approval of the platform security review. This adds application safeguards; it does not certify deployment security or claim the system cannot be compromised.

## Administrator sign-in

Every active platform operator must complete password and email verification on sign-in. Remembered devices do not bypass verification. Access and refresh tokens require a saved session with MFA proof. Existing platform sessions without proof require a new sign-in; tenant sessions retain their existing behavior. Codes expire after five minutes, are consumed once, and retain attempt/request limits.

Recovery administration at `/internal/admin/` also requires password and a fresh email code. Recovery authority is limited to the platform owner and lasts fifteen minutes after verification. Security audit, login, failure and session records are read-only in recovery administration.

Email verification is not phishing resistant. Passkeys/security keys and stronger recovery procedures remain future work. Reliable production email delivery is necessary for this rollout.

## Separate platform duties

| Duty | Available responsibilities |
| --- | --- |
| Owner | Full existing platform operations, advanced administration and operator assignments |
| Security | Security summaries, sign-ins, session termination, login unlock, incidents, audit and health |
| Support | Existing platform support workflows |
| Subscriptions | Subscription catalogue/read access and plan changes; renewal/reactivation stays in owner-only advanced administration |
| Auditor | Read-only audit, incident register and health |

Platform operators inherit no company workspace permissions. Server permissions enforce duties independently of frontend navigation. Unrecognized duties have no privileges. Existing operators retain Owner so rollout does not silently remove authority; no live duty assignments were changed.

The owner can change an existing operator's duty through Platform access. Changes require the owner's current password, a reason and the expected previous duty. Concurrent edits are rejected; at least one usable owner must remain. A changed operator's sessions are ended and the action is audited. This editor does not create or elevate new platform accounts.

## Incident register

Security operators and owners can record incidents with severity, evidence note and password confirmation. Incidents are assigned to their creator. Investigation history records each actor, note and status change. Allowed transitions include investigation, containment, resolution and reopening; stale edits are rejected and resolution dates are tracked. Auditors can read without modifying. API deletion and generic updates are unavailable.

Statuses document human actions; marking an incident contained does not automatically terminate sessions or execute other containment. Reassignment, attachments, automated incident detection and external alert delivery are not implemented in this pass.

## Measured health

Database and cache checks measure current availability. The reporting maintenance task records successful or failed runs in the shared cache; production runs every minute and evidence older than three minutes is unhealthy. The monitor describes only this reporting task, not all background workers. Local process-only cache cannot provide cross-process reporting evidence; production requires its configured shared Redis cache.

Email delivery, private storage and backup/restore checks show Not monitored until real deployment evidence is connected. An overall Partially monitored state replaces a misleading blanket Healthy label. Existing email backend configuration remains diagnostic data, not proof of delivered email.

## Rollout and verification

Additive migrations `users.0006`, `platform_admin.0001_initial`, `security.0005` and permission-choice migration `organizations.0014` were applied locally. Deploy migrations before the corresponding application workers, and deploy token issuance, verification and refresh together. Existing platform sessions must sign in again. No live permissions or incidents were created during verification.

Tests cover duty boundaries, owner protection, session revocation after duty changes, incident history and stale edits, mandatory OTP despite a trusted device, real bearer/refresh rejection without MFA, verified OTP session issuance, recovery login template/session proof, evidence expiry and honest monitoring states. Frontend type and targeted style checks passed. The final security regression selection passed all 66 tests, including strict OpenAPI checks, session boundaries, platform duties, incidents, recovery authentication, subscription maintenance and reporting jobs. Django system checks and migration consistency checks passed. Schema-library typing deprecation warnings remain; no schema-generation errors were reported.

Live browser inspection confirmed an old platform session redirects to Login after reload. After the user signed in again, live dark-mode browser checks verified the dashboard, security center, incident register and creation form, operator-duty page and change form, navigation, and health cards. No incident or duty change was submitted. The overview incorrectly labelled partial monitoring as degraded; its badge was corrected and verified live. Frontend type and targeted lint checks passed after this correction. Proof: `platform-health-badge-verified.png` in the task visualization directory. Other operator-duty browser accounts and populated incident actions were not exercised live; their permission and transition checks passed in the test database.

## Remaining security work

Passkeys/security keys; independently protected audit storage; temporary support-access expansion; HttpOnly session/CSP migration; upload scanning; connected delivery/storage/backup monitors; production secret/proxy/infrastructure verification; restoration drills and independent staging assessment remain outside this completed application pass.


## Passkey follow-up

Optional administrator password-plus-passkey sign-in and personal credential management are now implemented. Email verification and recovery administration remain available. See [administrator passkeys](administrator-passkeys.md) for deployment configuration, verification and device-enrollment limitations.
