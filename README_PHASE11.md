# SmartBiz Phase 11 — Comprehensive Automated Tests & Integrated Verification

Phase 11 is a verification gate. It does not declare the backend production-ready merely because overlay modules compile.

## Required gates

1. Static/API contract: no `fields="__all__"`, canonical v1 routes, correct SimpleJWT settings, pagination/error/request-id contract.
2. Django integrity: `check`, `makemigrations --check --dry-run`, migration plan, clean PostgreSQL migration.
3. Security: tenant isolation, platform/tenant separation, sensitive capability boundaries, last-admin protection, session revocation, support isolation, anonymity propagation.
4. Concurrency: workflow actions, sequences, invite acceptance, employee replacement, subscription changes, record issuance, import commit, template application.
5. API: `/api/v1/`, `/api/platform/v1/`, `/internal/admin/`, stable errors, request IDs, pagination, allowed_actions, throttles, upload limits.
6. OpenAPI: generate and validate `openapi-v1.yaml`; diff future changes in CI.

## Known blockers from retrieved source

- Retrieved EmployeeProfile still has globally unique `employee_id`; production requires `(company, employee_id)` uniqueness.
- Existing platform tests still target legacy `/api/platform/...`; migrate to `/api/platform/v1/...`.
- Retrieved tenant DashboardView still contains a SUPERUSER tenant-aggregation branch. Platform identities must use the Platform Control Center instead.
- Platform URLs expose both `security/sessions` and `sessions`; choose one canonical v1 endpoint before OpenAPI freeze.

## Verification command

Run from the fully integrated repository root:

    python smartbiz_phase11/scripts/verify_backend.py

A true production verdict requires the complete merged Phase 1-10 repository, PostgreSQL, cache/Redis, migrations, private storage adapters, malware scanning integration, and all dependencies. SQLite is insufficient for row-lock/concurrency proof.
