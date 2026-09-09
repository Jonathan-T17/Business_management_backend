"""Phase 7 acceptance matrix.
Search: capability required; no platform tenant search; no private chat; no sensitive dynamic fields; source visibility preserved.
AI: capability+entitlement; source-scoped; anonymous identity preserved; HR/compensation/location/security excluded.
Exports/imports/bulk: source scope never widened; sensitive purpose required; no passwords/salary/platform roles; idempotent locked imports.
Activity: operational only; AuditLog authoritative; metadata sanitized; source visibility inherited.
Notifications: personal/tenant/platform security audiences separated; sensitive content generic; internal URLs only.
Chat: participant-only; no admin DM surveillance; scope eligibility; private attachments; soft delete/edit history.
Subscriptions: tenant can read own usage/entitlements but not mutate Plan; platform capability required for plan/subscription mutation.
"""
