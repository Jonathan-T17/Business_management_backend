from subscriptions.models import Subscription


def activate_subscription(company, plan):
    subscription, _ = Subscription.objects.update_or_create(
        company=company,
        defaults={
            "plan": plan,
            "is_active": True,
        }
    )
    return subscription