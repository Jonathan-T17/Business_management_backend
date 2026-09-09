# SmartBiz Phase 7 — Secondary Data Systems

Production invariant: a secondary system MUST NOT widen access granted by the source object.

Pipeline:
authentication → tenant/platform context → capability → subscription entitlement → source visibility → classification → derived action → audit.

Integration checklist:
1. Add/confirm capabilities GLOBAL_SEARCH, VIEW_COMPANY_ANALYTICS, GENERATE_AI_INSIGHTS, IMPORT_EMPLOYEES, EXPORT_OPERATIONAL_DATA, EXPORT_SENSITIVE_DATA, BULK_MANAGE_TASKS, USE_CHAT, MANAGE_CHAT, MANAGE_SUBSCRIPTION, PLATFORM_PLANS, PLATFORM_SUBSCRIPTIONS.
2. Replace direct Plan feature checks with EntitlementService.
3. Tenant subscription API is read-focused for current plan/usage/entitlements; Plan mutation is platform-only.
4. Global Search uses source visibility adapters, never TenantService; excludes chat and sensitive dynamic fields; platform search is separate.
5. Analytics/AI uses visibility-scoped querysets, classification filters, anonymity preservation, and entitlement checks.
6. Imports use private storage, malware scan, validation before commit, row lock/idempotency, and cannot set passwords/salary/platform authority.
7. Exports use source-scoped querysets; sensitive exports require capability + business purpose.
8. Activity feed is not AuditLog; sanitize metadata at write and enforce source visibility at read. Remove tenant activity from PlatformActivityViewSet.
9. Notifications split PERSONAL_SECURITY/TENANT_SECURITY/PLATFORM_SECURITY/OPERATIONAL; sensitive previews are generic; URLs internal; email after commit with retries.
10. Chat is membership-only; no SUPERUSER tenant bypass; no ADMIN DM surveillance; use private Attachment integration; global search excludes message bodies.
11. Migrations: ConversationMember moderator fields; Message private attachments; export/import classification and scan metadata; AI insight source scope/classification ceiling.
12. Production infrastructure: Redis/cache, worker queue, async analytics/email/import/export, private storage, retention jobs, background-job observability.
