"""Phase 10 acceptance matrix.
- /api/v1 tenant and /api/platform/v1 platform routes only; organizations included once.
- Schema/docs disabled outside DEBUG; Django Admin moved to /internal/admin/.
- Every collection paginated; ordering/search/filter fields allow-listed.
- Cross-tenant/unauthorized object lookup resolves through visible queryset and returns 404.
- No production serializer uses fields='__all__'; lifecycle/company/creator fields are explicit/read-only.
- Actionable objects expose backend-derived allowed_actions.
- Errors use stable code/message/request_id/fields envelope.
- Named throttles applied to login, verification, reset, invite, export/import, AI, public verify, security actions.
- Retriable mutations require Idempotency-Key; same key/different body rejected.
- State machines use transaction.atomic/select_for_update; editable configuration uses version/409 conflict.
- Upload size/type validation plus Phase 6 malware/private-storage policy.
- BLACKLIST_AFTER_ROTATION belongs in SIMPLE_JWT with ROTATE_REFRESH_TOKENS enabled.
"""
