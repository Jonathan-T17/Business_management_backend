from activity.models import ActivityLog


# activity/audit.py
class ActivityAudit:
    @staticmethod
    def log(*, 
            user, 
            company, 
            action, 
            project=None, 
            task=None, 
            metadata=None):
        ActivityLog.objects.create(
            company=company,
            project=project,
            task=task,
            user=user,
            action=action,
            metadata=metadata or {},
        )
