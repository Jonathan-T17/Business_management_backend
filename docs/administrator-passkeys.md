# Administrator passkeys

Passkeys add an optional device-verified second factor to platform administrator password sign-in. They do not change company-worker authentication, operator duties, confidential-data permissions or the existing email recovery path.

## User flow

1. Sign in with password and email verification. Open Platform navigation > My passkeys.
2. Within fifteen minutes of verified sign-in, give the passkey a recognizable name and confirm your password. Complete the device/browser prompt yourself. SmartBiz saves the public credential; it does not receive device PINs or biometric data.
3. On later sign-ins, enter your email and password and select Sign in with a passkey. Complete device verification. Regular Sign in continues to use email verification.
4. To remove a passkey, sign in recently, confirm your password and select Remove and sign out. Removal ends all administrator sessions and pending passkey requests. Another passkey or email verification can be used afterward.

Passkeys are personal. Owners cannot enroll or remove another person's keys. At most ten active keys are accepted per administrator. Lost-device administrative recovery, forced passkey policies, passwordless login and recovery-admin WebAuthn are not included; recovery administration continues to require email MFA. An email fallback means the account's overall recovery resistance still depends on email security.

## Server controls

The WebAuthn library verifies signatures, relying-party identity, expected origins, request challenge, user verification and signature counters. Login challenges are issued only after the password is verified for an active platform operator. Requests expire after three minutes, are one-use and are invalidated if the stored password changes. Registration is tied to the current verified saved session. Credentials are account-bound, unique, and excluded from duplicate enrollment; revoked credentials cannot be used again. Rejected login proofs are counted for lockout and audited. Endpoint rate limits apply.

One-use requests are consumed even when cryptographic verification fails. No access token is issued until verified device proof succeeds. New tokens retain existing session binding and revocation checks. Administrator duty changes, account disabling and password reset retain their existing authentication restrictions.

## Deployment

Install the pinned `webauthn==3.0.1` dependency and apply `security.0006_administratorpasskey_passkeychallenge` (applied locally) before application workers use these endpoints. Configure both:

- `WEBAUTHN_RP_ID`: the actual site domain, with no scheme or port, such as `app.example.com`.
- `WEBAUTHN_ORIGINS`: comma-separated exact HTTPS frontend origins, such as `https://app.example.com`. No wildcards, paths or request-derived hosts.

Development defaults use RP `localhost` and origin `http://localhost:3000`. A passkey enrolled at localhost does not work at 127.0.0.1 or the production domain. HTTP is accepted only for localhost in DEBUG mode. Missing or invalid deployment configuration disables passkeys while retaining email sign-in. Do not change the RP identity after enrollment without a migration/re-enrollment plan. Review domain ownership and security before enabling this in production.

The browser/device must support WebAuthn and run in a secure context. Some embedded browsers may not expose device credential prompts; use a supported browser on the configured origin. Browser/device enrollment requires the account holder; agent verification does not create live credentials.

## Verification

Frontend type and targeted lint checks passed. The broader security regression selection passed 69 tests; after adding explicit embedded-page rejection, all 15 focused passkey tests passed. These selections overlap. Django checks and migration consistency checks passed. Tests cover origin/challenge/signature/user-verification and embedded-page rejection, counter regression, request reuse/expiry, password changes, account ownership, stale management verification, and session revocation. Actual hardware enrollment and production-domain verification must be completed by the administrator.

Primary reference: https://duo-labs.github.io/py_webauthn/ and https://github.com/duo-labs/py_webauthn


## Local browser follow-up

The new sign-in button was visible in the live browser. A source-encoding build issue was corrected. The local backend was restored after being unavailable, and its restricted-network email failure was resolved by restarting it with approved network access. Live regular sign-in reached the email-code prompt afterward. Personal passkey-page verification and actual device enrollment still require the account holder to finish that sign-in. No live passkeys were created or removed.


After the user completed email verification, the live administrator passkey page and enrollment form loaded successfully in dark mode. The page showed an empty credential list, recognized recent MFA, and displayed name/password fields plus the device-verification action. No credential was created or removed. Enrollment was handed to the user; hardware verification remains pending. Screenshot: administrator-passkey-enrollment-ready.png in the task visualization directory.
