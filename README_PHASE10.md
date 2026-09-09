# SmartBiz Phase 10 — API Hardening & Contract Freeze

## Canonical API
Tenant: `/api/v1/...`  
Auth: `/api/v1/auth/...`  
Platform: `/api/platform/v1/...`  
Internal Django Admin: `/internal/admin/`

## Confirmed existing issues
- `organizations.urls` is mounted twice in the current root URL configuration.
- OpenAPI schema/Swagger are always mounted.
- REST Framework has no default pagination.
- `BLACKLIST_AFTER_ROTATION` is inside `REST_FRAMEWORK` instead of `SIMPLE_JWT`.
- Several production serializers still use `fields="__all__"`.
- Some apps implement custom pagination instead of one shared contract.

## Frozen request pipeline
Authentication → account/company state → tenant/platform context → capability → visible queryset → organizational scope → Phase 9 classification → business state → subscription entitlement → allowed_actions → domain service → transaction/locks → authoritative audit → on_commit side effects.

## Tenant isolation
Object lookup must query the caller-visible queryset first. Do not fetch a global object and permission-check afterward. Cross-tenant/unauthorized identifiers intentionally return 404.

## Serializer contract
All public serializers use explicit fields. Adding a model field must never silently alter the API. State fields are modified only through dedicated domain actions. Sensitive fields use Phase 9 disclosure policies.

## Idempotency/concurrency
Use `Idempotency-Key` for retriable POST operations. Cache-backed support is included; financial/Official Record critical actions should use persistent DB idempotency records. Use row locks for state machines and optimistic integer versions for concurrently editable configuration; stale updates return 409.

## Integration before Phase 11
1. Replace root routes with canonical versioned routes and remove aliases.
2. Merge Phase 10 REST/JWT settings into real settings.
3. Add RequestIDMiddleware.
4. Replace all remaining `fields="__all__"` serializers.
5. Add domain allowed_actions to actionable serializers.
6. Convert direct object lookups to visibility-scoped lookup.
7. Attach named throttle classes to high-risk endpoints.
8. Make submit/approve/reject/return/fulfill/import/export/record-generation idempotent where retriable.
9. Add version fields to concurrently editable configuration models.
10. Generate and diff OpenAPI in CI.

## Next
Phase 11 — comprehensive automated tests and integrated backend verification.
