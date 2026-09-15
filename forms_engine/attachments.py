from core.classification import DisclosureMode
from core.classification_policy import ClassificationPolicy
from .access import FormAccess
from .policy import FormSubmissionDisclosurePolicy


def can_read_files(user, submission):
    # A file may contain any answer: require clearance for every schema classification.
    return all(ClassificationPolicy.decision(user=user, classification=value,
        owner_id=submission.submitted_by_id, hide_when_denied=False).mode == DisclosureMode.FULL
        for value in FormSubmissionDisclosurePolicy.schema_for(submission).values())


def can_edit_files(user, submission):
    if not FormAccess.can_submit(user) or submission.company_id != user.company_id or submission.submitted_by_id != user.pk:
        return False
    if submission.status not in {'DRAFT', 'RETURNED'}:
        return False
    source = getattr(submission, 'business_request', None)
    return source is None or (source.requester_id == user.pk and source.status in {'DRAFT', 'RETURNED'})


def can_upload_files(user, submission):
    if not can_edit_files(user, submission):
        return False
    source = getattr(submission, 'business_request', None)
    return source is None or not source.request_type_definition_id or source.request_type_definition.attachments_allowed
