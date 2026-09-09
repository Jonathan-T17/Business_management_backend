def business_request_snapshot(obj):
    requester = obj.requester
    return {
        "request_number": obj.request_number,
        "request_type": obj.request_type,
        "title": obj.title,
        "description": obj.description,
        "priority": obj.priority,
        "amount": str(obj.amount) if obj.amount is not None else None,
        "currency": obj.currency,
        "quantity": str(obj.quantity) if obj.quantity is not None else None,
        "unit": obj.unit,
        "needed_by": obj.needed_by.isoformat() if obj.needed_by else None,
        "requester": {
            "id": str(obj.requester_id),
            "name": requester.full_name if requester else None,
            "email": requester.email if requester else None,
        },
        "branch": obj.branch.name if obj.branch else None,
        "department": obj.department.name if obj.department else None,
        "status": obj.status,
    }


def workflow_approval_snapshot(workflow_instance):
    result = []
    steps = workflow_instance.steps.prefetch_related(
        "recipients__user",
        "action_logs__actor",
    ).order_by("order")

    for step in steps:
        result.append({
            "step": step.name,
            "order": step.order,
            "status": step.status,
            "recipients": [
                {
                    "name": recipient.user.full_name,
                    "email": recipient.user.email,
                }
                for recipient in step.recipients.all()
            ],
            "actions": [
                {
                    "actor": action.actor.full_name if action.actor else None,
                    "action": action.action,
                    "timestamp": action.created_at.isoformat(),
                    "delegated": action.metadata.get("delegated", False),
                }
                for action in step.action_logs.all()
            ],
        })

    return result