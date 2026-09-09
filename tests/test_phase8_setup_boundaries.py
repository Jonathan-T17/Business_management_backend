"""
Phase 8 production acceptance matrix.

Authorization
-------------
- Platform SUPERUSER without tenant Support Mode cannot enter company setup.
- MANAGE_COMPANY_SETUP is required; role=ADMIN alone is insufficient.
- Setup configuration never grants content visibility by itself.
- Company cannot assign PLATFORM_ONLY capabilities.
- Sensitive capability grant requires actor to possess the sensitive authority.
- Last active Company Admin protections remain enforced by lifecycle services.

Readiness
---------
- onboarding_completed cannot be set by serializer PATCH.
- finish derives readiness server-side.
- required steps cannot be skipped.
- incomplete company profile blocks finish.
- absence of a safe role preset blocks finish.
- warning-only issues are returned but do not falsely mark setup complete.

Templates
---------
- applying the same business template twice is idempotent.
- applying a template never deletes company customizations.
- template references cannot point to another tenant.
- template application is transactional and audited.

Builders
--------
- approval routes validate every recipient against tenant/scope.
- approval route codes use collision-safe generation, not count()+1.
- reporting process codes use collision-safe generation.
- published form/workflow definitions are versioned rather than mutated.
- request type workflow/form belongs to company.
- field activity template location requirement triggers precise-location warning.
- official record policy validates source type and numbering policy.
- notification policy cannot reroute personal/tenant security events to platform.

Frontend contract
-----------------
- status returns server-derived readiness.
- status returns backend-derived allowed_actions.
- sensitive capabilities include warning metadata.
- all configuration serializers use explicit fields.
- no normal setup action requires Django Admin, shell, JSON editing, or SQL.
"""
