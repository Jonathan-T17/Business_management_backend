# SmartBiz AI — Phase 6: Business Records & Operations

This package is the production-hardening reference implementation for Documents, Attachments, Field Operations, Planning, and Official Records. Integrate it on top of Phases 1–5 rather than as an independent greenfield app.

## Production invariants

1. Files are private by default. API serializers never expose raw `FileField.url` values.
2. Downloads are authorized at request time and use short-lived signed URLs or an authenticated streaming endpoint.
3. Attachment access is inherited from the parent object and can never widen source visibility.
4. Attachment upload also requires authorization to the parent object.
5. MIME type, extension and file size must be server validated; production uploads must pass malware scanning before becoming downloadable.
6. Sensitive document categories require an explicit sensitive-document capability; Company Admin is not automatically a sensitive-document reader.
7. Document versions are append-only. Version creation and `current_version` changes happen in one transaction under a row lock.
8. Archived documents cannot silently receive new versions.
9. Field operations use event-based location capture only. SmartBiz must not implement continuous background employee tracking.
10. Exact latitude/longitude is `PRECISE_LOCATION` and is redacted unless the caller has `VIEW_FIELD_LOCATION`.
11. Arriving at a stop does not run completion requirements. Completing a stop does. Completing an activity validates its own completion requirements and all stops.
12. Audit metadata must not contain raw GPS coordinates.
13. Planning visibility is object-scoped. `MANAGEMENT` plans require an explicit management-plan capability and PlanItem visibility always inherits the parent plan.
14. Planning lifecycle is service controlled; generic PATCH may not directly force lifecycle states.
15. Official Records inherit source visibility and preserve or strengthen source classification.
16. Platform Superuser is not a tenant Official Record reader/issuer/voider by default.
17. Official Record issuance is source-aware through `OfficialRecordFinalizer`; generic workflow code must not build snapshots.
18. Record sequence allocation remains transactional and row locked.
19. Corrections produce a replacement record and preserve the superseded record. Core record fields remain immutable.
20. Public verification returns authenticity metadata only and must be rate limited.
21. Sensitive record export requires a reason/purpose and authoritative audit.
22. Search/AI/analytics/export later must respect the classification stored on the record.

## Required schema refinements

### Document
- `classification` CharField, default `NORMAL`.
- `current_version` stays server controlled.
- unique `(document, version_number)` on DocumentVersion.
- optionally add `archived_at`, `archived_by`, `archive_reason`.

### Attachment
- `scan_status`: PENDING/CLEAN/BLOCKED/FAILED.
- `sha256` checksum.
- optional `classification`, otherwise inherit from parent.
- never permit `company=None` tenant attachments.

### Field evidence
Prefer an explicit evidence model or classified Attachment metadata containing:
- evidence kind
- stop/activity relation
- capture timestamp
- classification
- checksum
Do not store precise coordinates in generic audit metadata.

### OfficialRecord
Add:
- `classification`
- `correction_reason`
- keep `source_version`
- preserve `approval_snapshot`
- keep immutable verification token and record number

Add indexes on `(company, classification, status)` where useful.

## Serializer/API contract

Document/Attachment representations expose file metadata, not storage URLs. Add explicit actions such as `/download/`, `/archive/`, `/restore/`, `/versions/`.

FieldStop serializers call `FieldAccessService.redact_stop()` or equivalent so `latitude` and `longitude` never reach unauthorized clients.

OfficialRecord detail serializers must redact snapshot fields whose classification exceeds caller authority. List serializers should remain summary-only.

All these serializers should expose backend-derived `allowed_actions`.

## Private storage

Production storage should be a private S3/GCS/Azure-compatible bucket/container. Disable anonymous reads and directory listing. Use short-lived signed URLs after backend authorization, or stream through the API. Add upload limits, allow-list MIME types, filename normalization, checksum, malware scan quarantine and retention cleanup.

## Acceptance tests

Documents: cross-company isolation; platform exclusion; Company Admin cannot see sensitive category by default; management document capability; raw URL absent; signed URL expires; version concurrency; archive rules; attachment parent inheritance; upload actor authority; malware-blocked files never downloadable.

Field Operations: worker/manager authority; no continuous tracking API; precise location redaction; arrive does not call completion validator; complete-stop does; complete-activity does; incomplete stops block completion; no GPS in audit metadata; invalid org assignment blocked.

Planning: cross-company isolation; management visibility capability; private owner visibility; branch/department visibility; PlanItem inherits parent visibility; lifecycle transition matrix; immutable archived plan; project/task structural consistency.

Official Records: source visibility inheritance; sensitive classification capability; platform exclusion; issuance capability; source-aware snapshots; concurrent sequence uniqueness; duplicate finalization idempotency; correction supersession; void reason; immutable number/snapshot; public verification does not expose snapshot; verification throttle; sensitive export requires purpose.

## Integration point from Phase 5

Replace the generic workflow-side official record creation with:

```python
from records_management.finalizer import OfficialRecordFinalizer
OfficialRecordFinalizer.finalize(source=target, actor=actor, request=request, trigger_status="APPROVED")
```

The source domain decides *when* finalization is valid; the finalizer decides *what authoritative snapshot* to create.
