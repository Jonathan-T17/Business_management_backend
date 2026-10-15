# Upload release checks — 12 October 2026

Prepared a private ClamAV Compose override and an application verification command.
See deployment/docker-compose.scanner.yml and the scanner section of deployment/RUNBOOK.md.

The scanner has no published host port or company-media mount, persists signatures,
and shares an internal network with the backend. Its separate update network permits
signature downloads. The backend waits for the official image healthcheck. Operators
must review and pin the image, provision resources, and verify daemon limits.

The verification command refuses missing scanner configuration, requires explicit
clean/rejected verdicts and supports an in-memory harmless antivirus detection probe
and the application's 25 MiB limit. It does not store uploads or alter company data.
The protocol adapter now rejects truncated, disconnected, unexpected and error
responses instead of accepting an incomplete clean response.

Verification performed locally:
- 52 focused non-database tests passed; 4 database tests were intentionally deselected
  because these changes concern scanner protocol, deployment structure and validation.
- Deployment YAML structure tested for private network, no host port, no company
  file mount and backend health dependency. Docker Compose's actual config/build/run
  validation could not run because Docker is unavailable on this computer.
- The application probe refused to proceed with the current unconfigured scanner:
  no false clean or detection success was reported.

Real scanner detection and staging uploads have NOT been verified. Neither Docker
nor ClamAV is available here. Run the documented commands on the staging/deployment
host, verify clean and detection probes, then test a scanner outage and retry on an
isolated staging draft. Confirm rejected files create no storage objects. Do not
perform the outage check against live production.

Physical-phone typing, picker and gesture checks remain outstanding. Browser
viewport checks previously passed at 390×844 and 1280×900; those are not physical
device tests. The administrator/employee/manager live journey passed and retained
its clearly marked test artifacts as documented in forms-end-to-end-2026-10-12.md.

No production service was launched, no local security setting was weakened, and no
company records or access grants were changed in this release-check step.

Official reference: https://docs.clamav.net/manual/Installing/Docker.html
