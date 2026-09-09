# SmartBiz Phase 9 — Cross-Module Sensitive Data Classification

## Core rule
Object visibility answers whether a user may know an object exists. Classification answers which fields and derived representations may be disclosed. Both are required.

## Canonical classifications
NORMAL, PERSONAL, FINANCIAL, HR_CONFIDENTIAL, COMPENSATION, PRECISE_LOCATION, SECURITY_SENSITIVE, MANAGEMENT_CONFIDENTIAL.

## Production disclosure pipeline
authentication → tenant/platform context → object visibility → organizational scope → classification → field-level disclosure → business state → entitlement → derived-system restrictions → allowed_actions → audit.

## Required migrations
Add classification where absent: Report/ReportField, FormField/schema snapshots, RequestTypeDefinition/BusinessRequest, DocumentCategory/Document/Attachment, OfficialRecord, AIInsight/export logs.
Migrate DocumentCategory.sensitive=True with no explicit type to MANAGEMENT_CONFIDENTIAL. Coordinates are PRECISE_LOCATION. Salary/compensation is COMPENSATION. Confidential HR notes are HR_CONFIDENTIAL. Security artifacts are SECURITY_SENSITIVE.

## Serializer rule
Never treat object visibility as proof every field is disclosable. Use explicit classification-aware serializers; remove fields='__all__' from sensitive surfaces.

## Anonymous-source rule
is_anonymous=True propagates into serializers, workflows, notifications, email context, activity, audit, exports, official records, analytics, AI, search, and support. No role-based reveal exception.

## Verified existing issues addressed
- Request CSV export can emit requester email for every visible request.
- Generic SECURITY digest can aggregate personal/tenant security events for platform superusers.
- DocumentCategory uses only a boolean sensitive flag.
- Sensitive secondary serializers need explicit field contracts.

## Next
Phase 10 — API hardening & contract freeze.
