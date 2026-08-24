from django.core.management.base import BaseCommand
from subscriptions.models import Plan

class Command(BaseCommand):
    help = "Ensure baseline subscription plans exist (Starter, Pro, Enterprise)."

    def handle(self, *args, **options):
        baseline_plans = [
            {
                "name": "Starter",
                "max_users": 5,
                "max_projects": 3,
                "ai_analytics_enabled": False,
                "reports_enabled": True,
                "price_monthly": 0.00,
                "is_active": True,
            },
            {
                "name": "Pro",
                "max_users": 50,
                "max_projects": 20,
                "ai_analytics_enabled": True,
                "reports_enabled": True,
                "price_monthly": 49.99,
                "is_active": True,
            },
            {
                "name": "Enterprise",
                "max_users": 500,
                "max_projects": 200,
                "ai_analytics_enabled": True,
                "reports_enabled": True,
                "price_monthly": 199.99,
                "is_active": True,
            },
        ]

        for plan_data in baseline_plans:
            plan, created = Plan.objects.get_or_create(
                name=plan_data["name"],
                defaults=plan_data,
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created plan: {plan.name}"))
            else:
                # Optionally update fields if plan exists but values differ
                updated = False
                for field, value in plan_data.items():
                    if getattr(plan, field) != value:
                        setattr(plan, field, value)
                        updated = True
                if updated:
                    plan.save()
                    self.stdout.write(self.style.WARNING(f"Updated plan: {plan.name}"))
                else:
                    self.stdout.write(self.style.NOTICE(f"Plan already correct: {plan.name}"))
