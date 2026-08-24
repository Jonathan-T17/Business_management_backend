from django.contrib import admin

from subscriptions.models import Plan, Subscription

# Register your models here.



@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "max_users", "max_projects")
    list_filter = ("ai_analytics_enabled", "reports_enabled")

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("company", "plan", "is_active")
    list_filter = ("is_active", "plan")