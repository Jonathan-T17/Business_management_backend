"""Phase 9 acceptance matrix.
- Object visibility does not imply field disclosure.
- Company ADMIN and platform SUPERUSER do not automatically disclose COMPENSATION, HR_CONFIDENTIAL, PRECISE_LOCATION, SECURITY_SENSITIVE or MANAGEMENT_CONFIDENTIAL.
- Anonymous reports omit identity from serializers, notifications, audit, exports, records, AI, search and support.
- Protected classifications are excluded from generic search/AI.
- Sensitive exports require source visibility, sensitive capability and business purpose.
- Official Record classification cannot be weaker than source classification.
- Support tickets grant communication, not protected tenant-data access.
- Audit metadata excludes credentials, OTPs, tokens, coordinates, compensation and private messages.
"""
