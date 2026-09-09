from django.db import transaction
from django.utils import timezone


def company_local_date(company, now=None):
    """Return the company's local date while preserving UTC storage globally."""
    from zoneinfo import ZoneInfo

    now = now or timezone.now()
    zone_name = getattr(company, "timezone", None) or "UTC"
    try:
        zone = ZoneInfo(zone_name)
    except Exception:
        zone = ZoneInfo("UTC")
    return now.astimezone(zone).date()


class CompanySequenceService:
    """Adapter around records_management.RecordSequence for business identifiers."""

    @classmethod
    @transaction.atomic
    def next(cls, *, company, prefix, date=None, width=5):
        from records_management.models import RecordSequence

        date = date or company_local_date(company)
        row, _ = RecordSequence.objects.select_for_update().get_or_create(
            company=company,
            prefix=prefix,
            year=date.year,
            defaults={"last_number": 0},
        )
        row.last_number += 1
        row.save(update_fields=["last_number"])
        return f"{prefix}-{date:%Y%m%d}-{row.last_number:0{width}d}"
