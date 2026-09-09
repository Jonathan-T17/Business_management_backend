import hashlib


class PublicVerificationService:
    """Return only authenticity metadata. Never expose record snapshots publicly."""

    @staticmethod
    def response(record):
        return {
            "valid": record.status == "ACTIVE",
            "record_number": record.record_number,
            "company": record.company.name,
            "record_type": record.record_type,
            "issued_at": record.issued_at,
            "status": record.status,
            "superseded": record.status == "SUPERSEDED",
        }

    @staticmethod
    def fingerprint(token):
        return hashlib.sha256(str(token).encode("utf-8")).hexdigest()
